"""Testes do servidor MCP do DevOps Pulse AI.

Cobrem:
- cliente MCP oficial em memória (descoberta e chamada de ferramentas);
- ponta a ponta real via Streamable HTTP (uvicorn + cliente oficial);
- transporte stdio (subproceso ``python -m app.mcp_server``);
- o protocolo JSON-RPC "no fio" exatamente como o navegador do dashboard envia;
- parâmetros inválidos e falhas controladas da API do GitHub.
"""

from __future__ import annotations

import asyncio
import json
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
import uvicorn
from mcp import Client, StdioServerParameters

from app.config import PROJECT_ROOT
from app.github_client import GitHubAPIError, GitHubClient
from app.main import app
from app.mcp_server import mcp as mcp_server

EXPECTED_TOOLS = {
    "get_repository_metrics",
    "get_commit_activity",
    "get_pull_requests",
    "get_issues",
    "analyze_repository_health",
    "run_stress_test",
    "run_full_bulletin",
}


def _tool_json(result: Any) -> dict[str, Any]:
    """Extrai o JSON de texto de um resultado de ferramenta bem-sucedido."""
    text = next((c.text for c in result.content if getattr(c, "type", None) == "text"), None)
    assert text, "resultado sem conteúdo textual"
    return json.loads(text)


def _error_text(result: Any) -> str:
    return " ".join(getattr(c, "text", "") for c in result.content)


# ---------------------------------------------------------------------------
# Cliente oficial em memória — sem rede
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lists_all_tools():
    async with Client(mcp_server) as client:
        result = await client.list_tools()
        names = {t.name for t in result.tools}
        assert names == EXPECTED_TOOLS
        for tool in result.tools:
            assert tool.description, f"ferramenta {tool.name} sem descrição"


@pytest.mark.asyncio
async def test_get_repository_metrics_demo():
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_repository_metrics",
            {"owner": "octocat", "repo": "hello-world", "hours": 24, "demo": True},
        )
        assert not result.is_error, _error_text(result)
        data = _tool_json(result)
        assert data["repository"] == "octocat/hello-world"
        assert data["data_source"] == "demo"
        assert data["metrics"]["commits"] == 8
        assert isinstance(data["alerts"], list)
        assert data["period"]["from"] < data["period"]["to"]
        assert any("DEMONSTRAÇÃO" in n for n in data["notes"])


@pytest.mark.asyncio
async def test_get_commit_activity_demo():
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_commit_activity",
            {"owner": "octocat", "repo": "hello-world", "hours": 24, "demo": True},
        )
        assert not result.is_error, _error_text(result)
        data = _tool_json(result)
        assert data["total_commits"] == 8
        assert sum(d["commits"] for d in data["daily_series"]) == 8
        assert len(data["latest_commits"]) == 8
        assert data["latest_commits"][0]["message"]


@pytest.mark.asyncio
async def test_get_pull_requests_state_filter_demo():
    async with Client(mcp_server) as client:
        open_result = await client.call_tool(
            "get_pull_requests",
            {"owner": "octocat", "repo": "hello-world", "state": "open", "demo": True},
        )
        assert not open_result.is_error, _error_text(open_result)
        data = _tool_json(open_result)
        assert data["count"] == 3
        assert all(item["state"] == "open" for item in data["items"])
        assert {"number", "title", "state", "created_at", "closed_at", "merged_at"} <= set(data["items"][0])

        all_result = await client.call_tool(
            "get_pull_requests",
            {"owner": "octocat", "repo": "hello-world", "state": "all", "demo": True},
        )
        assert _tool_json(all_result)["count"] == 5


@pytest.mark.asyncio
async def test_get_issues_excludes_pull_requests():
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_issues",
            {"owner": "octocat", "repo": "hello-world", "state": "closed", "demo": True},
        )
        assert not result.is_error, _error_text(result)
        data = _tool_json(result)
        # Dados demo: 6 issues reais (3 fechadas); a API do GitHub mistura PRs, aqui não.
        assert data["count"] == 3
        assert all("pull_request" not in item for item in data["items"])


@pytest.mark.asyncio
async def test_analyze_repository_health_demo():
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "analyze_repository_health",
            {"owner": "octocat", "repo": "hello-world", "hours": 24, "demo": True},
        )
        assert not result.is_error, _error_text(result)
        data = _tool_json(result)
        assert data["data_source"] == "demo"
        criterios = {o["criterio"] for o in data["observations"]}
        assert {"ci_success_rate", "stale_pull_requests", "issue_volume", "activity_volume"} <= criterios
        assert data["criteria"]["low_ci_success_rate"] == 80.0
        # Sem índice arbitrário: cada critério vem com limiar e limitações documentadas.
        assert data["limitations"]
        assert "metrics" in data and "alerts" in data


# ---------------------------------------------------------------------------
# Ferramentas com efeitos laterais: run_stress_test e run_full_bulletin
# ---------------------------------------------------------------------------


def test_app_stress_against_real_server(live_server):
    """Núcleo compartilhado (app.stress) mede um servidor HTTP real de ponta a ponta."""
    from app.stress import run_stress

    base = live_server.rsplit("/mcp", 1)[0]
    report = run_stress(
        requests="2,3", concurrency=2, endpoint="/health", base_url=base, timeout_s=10.0
    )
    assert report["endpoint"] == "/health"
    assert report["total_requests"] == 5
    assert report["total_success"] == 5
    assert report["overall_success_rate"] == 100.0
    batch = report["batches"][0]
    assert batch["requests"] == 2
    assert batch["concurrency"] == 2
    assert batch["p95_latency_ms"] is not None and batch["p95_latency_ms"] >= 0
    assert batch["requests_per_second"] > 0
    assert batch["sample_errors"] == []


def test_stress_validation_rejects_non_whitelisted_target():
    """Somente endpoints locais whitelisted e base localhost (nada de URL arbitrária)."""
    from app.stress import parse_requests, validate_target

    with pytest.raises(ValueError, match="não permitido"):
        validate_target("/etc/passwd")
    with pytest.raises(ValueError, match="base_url"):
        validate_target("/health", "http://exemplo.com")
    with pytest.raises(ValueError, match="1 e 50"):
        parse_requests("51")
    with pytest.raises(ValueError, match="3 lotes"):
        parse_requests("1,2,3,4")
    assert parse_requests("5,10") == [5, 10]


@pytest.mark.asyncio
async def test_run_stress_test_tool_wiring(monkeypatch):
    """A ferramenta MCP repassa parâmetros validados e devolve o relatório."""
    captured: dict[str, Any] = {}

    def fake_run_stress(**kwargs):
        captured.update(kwargs)
        return {
            "base_url": "http://127.0.0.1:8000",
            "endpoint": kwargs.get("endpoint"),
            "concurrency": kwargs.get("concurrency"),
            "batches": [],
            "total_requests": 5,
            "total_success": 5,
            "overall_success_rate": 100.0,
        }

    monkeypatch.setattr("app.mcp_server.run_stress", fake_run_stress)
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "run_stress_test",
            {"requests": "2,3", "concurrency": 2, "endpoint": "/health"},
        )
        assert not result.is_error, _error_text(result)
        data = _tool_json(result)
        assert data["tool"] == "run_stress_test"
        assert data["overall_success_rate"] == 100.0
        assert data["notes"]
        assert captured["requests"] == "2,3"
        assert captured["concurrency"] == 2
        assert captured["endpoint"] == "/health"

        # Endpoint fora da whitelist → erro controlado.
        bad = await client.call_tool("run_stress_test", {"endpoint": "/admin"})
        assert bad.is_error


@pytest.mark.asyncio
async def test_run_full_bulletin_demo_no_side_effects():
    """Pipeline completo em modo demo, sem LLM/TTS/WhatsApp: só dados + SQLite."""
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "run_full_bulletin",
            {
                "hours": 24,
                "with_llm": False,
                "with_tts": False,
                "send_whatsapp": False,
                "demo": True,
            },
        )
        assert not result.is_error, _error_text(result)
        data = _tool_json(result)
        assert data["tool"] == "run_full_bulletin"
        assert data["data_source"] == "demo"
        assert data["execution_id"].startswith("PULSE-")
        assert data["status"] in {"success", "partial"}
        assert data["metrics"]["commits"] >= 0
        assert isinstance(data["alerts"], list)
        assert data["bulletin"] and "PULSE" in data["bulletin"]
        # Sem envio: WhatsApp nulo e nota explícita.
        assert data["whatsapp"] is None
        assert "send_whatsapp=false" in data["audio_note"]
        assert "DADOS DEMO" in data["audio_note"]
        assert data["timings_ms"]["total_pipeline_latency_ms"] >= 0


@pytest.mark.asyncio
async def test_run_full_bulletin_whatsapp_disabled_is_clear():
    """send_whatsapp=true com WhatsApp desligado → mensagem clara, sem tentativa de rede."""
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "run_full_bulletin",
            {"with_llm": False, "with_tts": False, "send_whatsapp": True, "demo": True},
        )
        assert not result.is_error, _error_text(result)
        data = _tool_json(result)
        assert "WHATSAPP_ENABLED=false" in data["audio_note"]


# ---------------------------------------------------------------------------
# Parâmetros inválidos e falhas controladas
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_owner_is_controlled_error():
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_repository_metrics",
            {"owner": "../../etc", "repo": "x", "demo": True},
        )
        assert result.is_error
        assert "owner" in _error_text(result)


@pytest.mark.asyncio
async def test_invalid_hours_is_controlled_error():
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_repository_metrics",
            {"owner": "octocat", "repo": "hello-world", "hours": 9999, "demo": True},
        )
        assert result.is_error
        assert "hours" in _error_text(result)


@pytest.mark.asyncio
async def test_unknown_tool_is_controlled_error():
    async with Client(mcp_server) as client:
        result = await client.call_tool("ferramenta_inexistente", {})
        assert result.is_error
        assert "ferramenta_inexistente" in _error_text(result)


@pytest.mark.asyncio
async def test_github_api_failure_is_controlled_error(monkeypatch):
    """Repositório inexistente/erro da API → erro compreensível, sem crash."""

    def fake_get(self, path, params=None):
        raise GitHubAPIError("Repositório não encontrado: sem-teste/nao-existe", status_code=404)

    monkeypatch.setattr(GitHubClient, "_get", fake_get)
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_repository_metrics",
            {"owner": "sem-teste", "repo": "nao-existe", "demo": False},
        )
        assert result.is_error
        text = _error_text(result)
        assert "não encontrado" in text


# ---------------------------------------------------------------------------
# Ponta a ponta real: Streamable HTTP (uvicorn + cliente oficial)
# ---------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server():
    """Sobe a API real (com MCP montado em /mcp) em uma porta livre."""
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not server.started:
        if time.time() > deadline or not thread.is_alive():
            raise RuntimeError("uvicorn não subiu a tempo")
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}/mcp"
    server.should_exit = True
    thread.join(timeout=10)


def test_streamable_http_end_to_end(live_server):
    """Um cliente MCP oficial conecta, descobre e executa ferramentas via HTTP."""

    async def run() -> None:
        async with Client(live_server) as client:
            tools = await client.list_tools()
            assert {t.name for t in tools.tools} == EXPECTED_TOOLS

            result = await client.call_tool(
                "get_repository_metrics",
                {"owner": "octocat", "repo": "hello-world", "hours": 24, "demo": True},
            )
            assert not result.is_error, _error_text(result)
            data = _tool_json(result)
            assert data["data_source"] == "demo"

            second = await client.call_tool(
                "get_commit_activity",
                {"owner": "octocat", "repo": "hello-world", "demo": True},
            )
            assert not second.is_error, _error_text(second)

    asyncio.run(run())


def test_stdio_transport_end_to_end():
    """Transporte stdio: subproceso `python -m app.mcp_server` (Claude Desktop)."""

    async def run() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "app.mcp_server"],
            # DEMO_MODE explícito para não depender do .env local; env var vence .env.
            env={"PYTHONPATH": str(PROJECT_ROOT), "DEMO_MODE": "true"},
        )
        async with Client(params) as client:
            tools = await client.list_tools()
            assert {t.name for t in tools.tools} == EXPECTED_TOOLS
            result = await client.call_tool(
                "get_repository_metrics",
                {"owner": "octocat", "repo": "hello-world", "demo": True},
            )
            # Se os logs corrompessem o stdout do stdio, a listagem acima já teria falhado.
            assert not result.is_error, _error_text(result)
            assert _tool_json(result)["data_source"] == "demo"

    asyncio.run(run())


# ---------------------------------------------------------------------------
# O "fio" JSON-RPC do navegador do dashboard (cliente MCP mínimo)
# ---------------------------------------------------------------------------


def _post_rpc(url: str, payload: dict[str, Any]) -> httpx.Response:
    """Envia JSON-RPC exatamente como o fetch() do dashboard (segue 307 /mcp → /mcp/)."""
    return httpx.post(
        url,
        json=payload,
        headers={
            "Origin": "null",  # página aberta via file://
            "Accept": "application/json, text/event-stream",
        },
        timeout=15.0,
        follow_redirects=True,
    )


def test_browser_jsonrpc_wire(live_server):
    # 1) Preflight CORS (o navegador faz OPTIONS antes do POST JSON).
    pre = httpx.options(
        live_server,
        headers={
            "Origin": "null",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=15.0,
    )
    assert pre.status_code in (200, 204), pre.text
    assert pre.headers.get("access-control-allow-origin") is not None

    # 2) initialize
    init = _post_rpc(
        live_server,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "devops-pulse-dashboard", "version": "1.0"},
            },
        },
    )
    assert init.status_code == 200, init.text
    server_info = init.json()["result"]["serverInfo"]
    assert server_info["name"] == "devops-pulse"

    # 3) notification initialized (sem id → resposta vazia/2xx)
    notif = _post_rpc(
        live_server,
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    assert notif.status_code < 300, notif.text

    # 4) tools/call como o botão da página faz
    call = _post_rpc(
        live_server,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_repository_metrics",
                "arguments": {"owner": "octocat", "repo": "hello-world", "hours": 24, "demo": True},
            },
        },
    )
    assert call.status_code == 200, call.text
    body = call.json()
    assert "error" not in body, body
    result = body["result"]
    assert not result.get("isError") and not result.get("is_error"), result
    text = next(c["text"] for c in result["content"] if c["type"] == "text")
    data = json.loads(text)
    assert data["data_source"] == "demo"

    # 5) Erro controlado chega como isError, sem derrubar a conexão.
    bad = _post_rpc(
        live_server,
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_repository_metrics",
                "arguments": {"owner": "x", "repo": "..", "demo": True},
            },
        },
    )
    assert bad.status_code == 200, bad.text
    assert bad.json()["result"].get("isError") is True
