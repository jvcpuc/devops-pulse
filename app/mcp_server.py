"""Servidor MCP (Model Context Protocol) do DevOps Pulse AI.

Expõe as consultas já existentes do projeto como ferramentas MCP **somente-leitura**,
reutilizando ``GitHubClient``, ``compute_metrics``, ``generate_alerts`` e
``build_demo_raw`` — sem duplicar regras de negócio.

Transportes suportados:

- **Streamable HTTP**: montado na API FastAPI existente em ``/mcp``
  (``http://127.0.0.1:8000/mcp``). Usado pela página do dashboard (cliente
  mínimo JSON-RPC no navegador) e por clientes MCP externos.
- **stdio**: ``python -m app.mcp_server`` — para clientes que iniciam o
  servidor como subproceso (ex.: Claude Desktop).

Decisão de transporte: o projeto já executa uma API HTTP local (uvicorn na
porta 8000). Montar o Streamable HTTP nela mantém um único processo/porta na
demonstração e permite que o navegador use o mesmo ponto de extremidade que um
cliente MCP externo. O modo ``json_response`` + ``stateless_http`` simplifica o
cliente do navegador (respostas JSON diretas, sem SSE e sem estado de sessão).
O transporte stdio é oferecido como alternativa para clientes desktop.
"""

from __future__ import annotations

import logging
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field
from starlette.applications import Starlette

from app import __version__
from app.alerts import generate_alerts
from app.config import get_settings
from app.demo_data import build_demo_raw
from app.github_client import GitHubAPIError, GitHubClient
from app.logging_config import get_logger, setup_logging
from app.metrics import compute_metrics
from app.pipeline import PulsePipeline
from app.stress import run_stress
from app.whatsapp_client import WhatsAppClient

logger = get_logger(__name__)

# Validação de owner/repo: impede injeção de caminho/URL nas ferramentas
# (nenhuma ferramenta aceita caminho de arquivo, comando ou URL arbitrários).
_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_REPO_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")

mcp = MCPServer(
    name="devops-pulse",
    title="DevOps Pulse AI",
    description=(
        "Métricas de repositórios GitHub (commits, issues, pull requests e CI) "
        "calculadas pelo projeto DevOps Pulse AI. Somente leitura."
    ),
    instructions=(
        "Servidor MCP do DevOps Pulse AI. As ferramentas get_repository_metrics, "
        "get_commit_activity, get_pull_requests, get_issues e analyze_repository_health "
        "são somente-leitura. Todos os resultados trazem 'data_source': quando for "
        "'demo', os números são fictícios de demonstração e não devem ser apresentados "
        "como dados reais do GitHub. Duas ferramentas têm efeitos laterais e devem ser "
        "usadas com consentimento do usuário: run_stress_test dispara carga controlada "
        "contra os endpoints locais do próprio microsserviço; run_full_bulletin executa "
        "o pipeline completo (LLM, áudio TTS e persistência) e ENVIA o boletim no "
        "WhatsApp configurado, anexando o áudio quando disponível."
    ),
    version=__version__,
)

OwnerParam = Annotated[
    str,
    Field(description="Usuário ou organização do GitHub (ex.: 'n8n-io')."),
]
RepoParam = Annotated[
    str,
    Field(description="Nome do repositório (ex.: 'n8n')."),
]
HoursParam = Annotated[
    int,
    Field(ge=1, le=168, description="Janela de análise em horas (padrão 24, máximo 168)."),
]
DemoParam = Annotated[
    bool | None,
    Field(
        description=(
            "true = forçar dados de demonstração; false = forçar GitHub real; "
            "omitir = usar a configuração do servidor (DEMO_MODE)."
        )
    ),
]


def _validate_repo(owner: str, repo: str) -> tuple[str, str]:
    owner = (owner or "").strip()
    repo = (repo or "").strip()
    if not _OWNER_RE.match(owner):
        raise ToolError(
            f"Parâmetro 'owner' inválido: {owner!r}. Use o nome do usuário/organização "
            "do GitHub (letras, números e hífen, sem espaços, barras ou URLs)."
        )
    if not _REPO_RE.match(repo) or repo in {".", ".."}:
        raise ToolError(
            f"Parâmetro 'repo' inválido: {repo!r}. Use apenas o nome do repositório "
            "(letras, números, ponto, sublinhado e hífen — sem '/' nem URLs)."
        )
    return owner, repo


def _now_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _collect(
    owner: str,
    repo: str,
    hours: int,
    demo: bool | None,
) -> dict[str, Any]:
    """Coleta dados brutos usando a lógica existente do projeto.

    Retorna o payload normalizado (formato do GitHubClient), o período consultado,
    o rotulo de fonte (github/demo) e as notas de limitação aplicáveis.
    """
    now = datetime.now(timezone.utc)
    window_end = now
    window_start = now - timedelta(hours=hours)
    settings = get_settings()
    use_demo = settings.demo_mode if demo is None else bool(demo)

    notes: list[str] = []
    if use_demo:
        raw = build_demo_raw(window_start, window_end)
        data_source = "demo"
        notes.append(
            "Dados de DEMONSTRAÇÃO fictícios (parâmetro demo=true ou DEMO_MODE do "
            "servidor) — não são dados reais do GitHub."
        )
    else:
        client = GitHubClient(settings, repo_full_name=f"{owner}/{repo}")
        try:
            raw = client.fetch_raw(window_start=window_start, window_end=window_end)
        except GitHubAPIError as exc:
            # Mensagem controlada para o cliente (rate limit, 404, timeout etc.).
            raise ToolError(f"Falha ao consultar o GitHub para {owner}/{repo}: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 — evita vazar detalhes internos
            logger.exception("Erro inesperado na coleta MCP")
            raise ToolError(
                f"Erro inesperado ao consultar {owner}/{repo}. Verifique a conexão e tente novamente."
            ) from exc
        data_source = "github"
        notes.append(
            "Coleta da primeira página da API do GitHub (até 100 itens por tipo) — "
            "sem paginação completa."
        )

    return {
        "raw": raw,
        "window_start": window_start,
        "window_end": window_end,
        "data_source": data_source,
        "notes": notes,
    }


def _base_envelope(
    tool: str,
    owner: str,
    repo: str,
    collected: dict[str, Any],
    hours: int,
) -> dict[str, Any]:
    return {
        "tool": tool,
        "status": "success",
        "repository": f"{owner}/{repo}",
        "data_source": collected["data_source"],
        "queried_at": _now_iso(collected["window_end"]),
        "period": {
            "from": _now_iso(collected["window_start"]),
            "to": _now_iso(collected["window_end"]),
        },
        "hours": hours,
        "notes": list(collected["notes"]),
    }


@mcp.tool(
    name="get_repository_metrics",
    description=(
        "Retorna as métricas gerais do DevOps Pulse para um repositório GitHub no "
        "período: commits, issues abertas/fechadas, pull requests abertos/fechados, "
        "PRs parados, execuções de CI (total/sucesso/falha/taxa) e alertas gerados. "
        "Somente leitura."
    ),
)
def get_repository_metrics(
    owner: OwnerParam,
    repo: RepoParam,
    hours: HoursParam = 24,
    demo: DemoParam = None,
) -> dict[str, Any]:
    """Métricas gerais + alertas (reutiliza compute_metrics/generate_alerts)."""
    owner, repo = _validate_repo(owner, repo)
    collected = _collect(owner, repo, hours, demo)
    settings = get_settings()

    metrics = compute_metrics(
        collected["raw"],
        window_start=collected["window_start"],
        window_end=collected["window_end"],
        stale_pr_days=settings.stale_pr_days,
    )
    alerts = generate_alerts(
        metrics,
        stale_pr_days=settings.stale_pr_days,
        low_ci_success_rate=settings.low_ci_success_rate,
        high_issue_volume=settings.high_issue_volume,
        unusual_activity_multiplier=settings.unusual_activity_multiplier,
    )

    payload = _base_envelope("get_repository_metrics", owner, repo, collected, hours)
    payload["metrics"] = metrics.as_dict()
    payload["alerts"] = [a.model_dump() for a in alerts]
    return payload


@mcp.tool(
    name="get_commit_activity",
    description=(
        "Retorna a atividade de commits de um repositório GitHub no período: total, "
        "série diária e amostra dos commits mais recentes (sha, data, mensagem). "
        "Somente leitura."
    ),
)
def get_commit_activity(
    owner: OwnerParam,
    repo: RepoParam,
    hours: HoursParam = 24,
    demo: DemoParam = None,
) -> dict[str, Any]:
    """Total + série diária de commits (reutiliza a coleta normalizada)."""
    owner, repo = _validate_repo(owner, repo)
    collected = _collect(owner, repo, hours, demo)

    from app.metrics import _parse_dt  # reutiliza o parser de datas do projeto

    commits = collected["raw"].get("commits") or []
    ws, we = collected["window_start"], collected["window_end"]

    in_window: list[dict[str, Any]] = []
    for c in commits:
        dt = _parse_dt(c.get("date"))
        if dt and ws <= dt <= we:
            in_window.append(c)

    daily: dict[str, int] = defaultdict(int)
    for c in in_window:
        dt = _parse_dt(c.get("date"))
        if dt:
            daily[dt.date().isoformat()] += 1

    payload = _base_envelope("get_commit_activity", owner, repo, collected, hours)
    payload["total_commits"] = len(in_window)
    payload["daily_series"] = [
        {"date": day, "commits": count}
        for day, count in sorted(daily.items())
    ]
    payload["latest_commits"] = [
        {
            "sha": (c.get("sha") or "")[:12],
            "date": c.get("date"),
            "message": c.get("message"),
        }
        for c in in_window[-10:]
    ][::-1]
    return payload


@mcp.tool(
    name="get_pull_requests",
    description=(
        "Lista os pull requests de um repositório GitHub com estado, datas e "
        "merged_at. Aceita filtro por estado (open, closed ou all). Somente leitura."
    ),
)
def get_pull_requests(
    owner: OwnerParam,
    repo: RepoParam,
    state: Annotated[
        Literal["open", "closed", "all"],
        Field(description="Estado dos pull requests: open, closed ou all (padrão all)."),
    ] = "all",
    limit: Annotated[int, Field(ge=1, le=100, description="Máximo de itens retornados (padrão 20).")] = 20,
    demo: DemoParam = None,
) -> dict[str, Any]:
    """Lista de PRs com filtro de estado (reutiliza a coleta normalizada)."""
    owner, repo = _validate_repo(owner, repo)
    # Janela longa: a lista de PRs não é limitada por período (apenas por página da API).
    collected = _collect(owner, repo, hours=168, demo=demo)

    pulls = collected["raw"].get("pull_requests") or []
    if state != "all":
        pulls = [p for p in pulls if p.get("state") == state]

    items = [
        {
            "number": p.get("number"),
            "title": p.get("title"),
            "state": p.get("state"),
            "created_at": p.get("created_at"),
            "closed_at": p.get("closed_at"),
            "merged_at": p.get("merged_at"),
        }
        for p in pulls[:limit]
    ]

    payload = _base_envelope("get_pull_requests", owner, repo, collected, hours=168)
    payload["state_filter"] = state
    payload["count"] = len(items)
    payload["items"] = items
    payload["notes"].append("PRs ordenados por atualização decrescente (primeira página da API).")
    return payload


@mcp.tool(
    name="get_issues",
    description=(
        "Lista as issues de um repositório GitHub (pull requests excluídos) com "
        "estado e datas. Aceita filtro por estado (open, closed ou all). "
        "Somente leitura."
    ),
)
def get_issues(
    owner: OwnerParam,
    repo: RepoParam,
    state: Annotated[
        Literal["open", "closed", "all"],
        Field(description="Estado das issues: open, closed ou all (padrão all)."),
    ] = "all",
    limit: Annotated[int, Field(ge=1, le=100, description="Máximo de itens retornados (padrão 20).")] = 20,
    demo: DemoParam = None,
) -> dict[str, Any]:
    """Lista de issues reais, sem PRs (reutiliza a coleta normalizada)."""
    owner, repo = _validate_repo(owner, repo)
    collected = _collect(owner, repo, hours=168, demo=demo)

    issues = collected["raw"].get("issues") or []
    if state != "all":
        issues = [i for i in issues if i.get("state") == state]

    items = [
        {
            "number": i.get("number"),
            "title": i.get("title"),
            "state": i.get("state"),
            "created_at": i.get("created_at"),
            "closed_at": i.get("closed_at"),
        }
        for i in issues[:limit]
    ]

    payload = _base_envelope("get_issues", owner, repo, collected, hours=168)
    payload["state_filter"] = state
    payload["count"] = len(items)
    payload["items"] = items
    payload["notes"].append(
        "Issues reais (a API do GitHub devolve PRs junto; eles são excluídos aqui)."
    )
    return payload


@mcp.tool(
    name="analyze_repository_health",
    description=(
        "Combina as métricas existentes em uma análise explicável de atividade e "
        "manutenção do repositório: observações com critérios e limites configurados. "
        "Não gera índice arbitrário nem avalia segurança. Somente leitura."
    ),
)
def analyze_repository_health(
    owner: OwnerParam,
    repo: RepoParam,
    hours: HoursParam = 24,
    demo: DemoParam = None,
) -> dict[str, Any]:
    """Análise explicável de atividade/manutenção com critérios documentados."""
    owner, repo = _validate_repo(owner, repo)
    collected = _collect(owner, repo, hours, demo)
    settings = get_settings()

    metrics = compute_metrics(
        collected["raw"],
        window_start=collected["window_start"],
        window_end=collected["window_end"],
        stale_pr_days=settings.stale_pr_days,
    )
    alerts = generate_alerts(
        metrics,
        stale_pr_days=settings.stale_pr_days,
        low_ci_success_rate=settings.low_ci_success_rate,
        high_issue_volume=settings.high_issue_volume,
        unusual_activity_multiplier=settings.unusual_activity_multiplier,
    )

    observations: list[dict[str, str]] = []

    # CI — critério documentado: taxa de sucesso x limiar configurado.
    if metrics.workflow_runs > 0:
        ok = metrics.workflow_success_rate >= settings.low_ci_success_rate
        observations.append(
            {
                "criterio": "ci_success_rate",
                "valor": f"{metrics.workflow_success_rate:.1f}% em {metrics.workflow_runs} execuções",
                "limiar_configurado": f"{settings.low_ci_success_rate:.0f}%",
                "interpretacao": (
                    "Dentro do limiar configurado."
                    if ok
                    else "Abaixo do limiar configurado — atenção à estabilidade de CI."
                ),
            }
        )
    else:
        observations.append(
            {
                "criterio": "ci_success_rate",
                "valor": "sem execuções de CI no período",
                "limiar_configurado": f"{settings.low_ci_success_rate:.0f}%",
                "interpretacao": "Não avaliável: sem dados de CI no período consultado.",
            }
        )

    observations.append(
        {
            "criterio": "stale_pull_requests",
            "valor": f"{metrics.stale_pull_requests} PR(s) aberto(s) há mais de {settings.stale_pr_days} dia(s)",
            "limiar_configurado": f"{settings.stale_pr_days} dias",
            "interpretacao": (
                "Nenhum PR parado pelo critério configurado."
                if metrics.stale_pull_requests == 0
                else "Há PRs parados — revisar o fluxo de revisão."
            ),
        }
    )

    observations.append(
        {
            "criterio": "issue_volume",
            "valor": (
                f"{metrics.issues_opened} aberta(s) e {metrics.issues_closed} fechada(s) no período; "
                f"{metrics.open_issues} aberta(s) no total da coleta"
            ),
            "limiar_configurado": f"{settings.high_issue_volume} abertas/ período",
            "interpretacao": (
                "Volume de issues dentro do limiar configurado."
                if metrics.issues_opened < settings.high_issue_volume
                else "Volume elevado de issues abertas no período."
            ),
        }
    )

    observations.append(
        {
            "criterio": "activity_volume",
            "valor": (
                f"{metrics.commits} commit(s), {metrics.pull_requests_opened} PR(s) aberto(s) "
                f"no período"
            ),
            "limiar_configurado": "sem limiar (informativo)",
            "interpretacao": "Volume de atividade do período, sem juízo de valor.",
        }
    )

    severity_count = {"high": 0, "medium": 0, "low": 0}
    for a in alerts:
        severity_count[a.severity] = severity_count.get(a.severity, 0) + 1

    payload = _base_envelope("analyze_repository_health", owner, repo, collected, hours)
    payload["metrics"] = metrics.as_dict()
    payload["alerts"] = [a.model_dump() for a in alerts]
    payload["observations"] = observations
    payload["alerts_by_severity"] = severity_count
    payload["criteria"] = {
        "stale_pr_days": settings.stale_pr_days,
        "low_ci_success_rate": settings.low_ci_success_rate,
        "high_issue_volume": settings.high_issue_volume,
        "source": "thresholds do projeto (arquivo de ambiente)",
    }
    payload["limitations"] = [
        "Esta análise descreve atividade e manutenção com base nos dados coletados; "
        "não é uma avaliação de segurança, qualidade de código ou maturidade do time.",
        "Não há pontuação composta: cada critério é apresentado separadamente com "
        "seu limiar configurado.",
        "Período limitado à janela informada (máx. 168 h) e à primeira página da API.",
    ]
    return payload


StressParam = Annotated[
    str,
    Field(
        description=(
            "Lotes de requisições separados por vírgula (ex.: '5,10'). Máximo 3 lotes "
            "de até 50 requisições cada."
        )
    ),
]
ConcurrencyParam = Annotated[
    int,
    Field(ge=1, le=20, description="Requisições simultâneas por lote (padrão 3, máximo 20)."),
]
StressEndpointParam = Annotated[
    Literal["/health", "/api/pulse"],
    Field(
        description=(
            "Endpoint local a medir (GET). '/health' é leve e mede o overhead da API; "
            "'/api/pulse' roda coleta+métricas a cada requisição (mais pesado)."
        )
    ),
]


@mcp.tool(
    name="run_stress_test",
    description=(
        "Executa um teste de estresse controlado contra os endpoints LOCAIS do próprio "
        "DevOps Pulse AI (/health ou /api/pulse) e retorna latência "
        "(média/mín/máx/p50/p95), taxa de sucesso e throughput por lote. Efeito lateral: "
        "gera carga real no microsserviço local — use com moderação. Limitado a 150 "
        "requisições por chamada e apenas endpoints locais whitelisted."
    ),
)
def run_stress_test(
    requests: StressParam = "5,10",
    concurrency: ConcurrencyParam = 3,
    endpoint: StressEndpointParam = "/health",
    timeout_s: Annotated[
        float, Field(ge=1, le=60, description="Timeout por requisição em segundos (padrão 30).")
    ] = 30.0,
) -> dict[str, Any]:
    """Teste de estresse do microsserviço local (reutiliza app/stress.py)."""
    try:
        report = run_stress(
            requests=requests,
            concurrency=concurrency,
            endpoint=endpoint,
            timeout_s=timeout_s,
        )
    except ValueError as exc:
        raise ToolError(str(exc)) from exc

    report["tool"] = "run_stress_test"
    report["notes"] = [
        "Carga aplicada ao microsserviço local em execução (a API que hospeda o MCP "
        "deve estar ativa — mesma máquina/porta 8000).",
        "Latências medidas do lado do cliente HTTP; incluem o tempo de resposta real "
        "do endpoint escolhido.",
    ]
    return report


@mcp.tool(
    name="run_full_bulletin",
    description=(
        "Executa o pipeline COMPLETO do DevOps Pulse AI (coleta → métricas → alertas → "
        "resumo com LLM local → boletim → áudio TTS → persistência no SQLite) e envia o "
        "boletim formatado no WhatsApp configurado, anexando o áudio do boletim quando "
        "disponível. ATENÇÃO: tem efeitos reais — consome Ollama/Kokoro locais, grava no "
        "banco e ENVIA mensagem no WhatsApp (WHATSAPP_TO). Use send_whatsapp=false para "
        "apenas executar o pipeline sem enviar."
    ),
)
def run_full_bulletin(
    hours: HoursParam = 24,
    with_llm: Annotated[
        bool, Field(description="Gerar resumo com o LLM local (Ollama). Padrão true.")
    ] = True,
    with_tts: Annotated[
        bool, Field(description="Gerar áudio do boletim (Kokoro/Edge). Padrão true.")
    ] = True,
    send_whatsapp: Annotated[
        bool,
        Field(description="Enviar o boletim no WhatsApp configurado (texto + áudio). Padrão true."),
    ] = True,
    demo: DemoParam = None,
) -> dict[str, Any]:
    """Pipeline completo + envio WhatsApp com áudio (efeitos laterais reais)."""
    settings = get_settings()

    # Pré-checagem da conexão: sem instância "open" o envio do pipeline falharia
    # com timeout (20s) — aqui falha rápido e com instrução clara de pareamento.
    wa = WhatsAppClient(settings)
    whatsapp_connected = False
    whatsapp_skip_reason: str | None = None
    if send_whatsapp and settings.whatsapp_enabled:
        conn_ok, conn = wa.connection_state()
        if not conn_ok or not conn.get("connected"):
            state = conn.get("state", "desconhecido")
            whatsapp_skip_reason = (
                f"WhatsApp NÃO conectado (estado: '{state}') — pipeline executado, "
                "mas NADA foi enviado. Clique em 'Mostrar QR do WhatsApp' no dashboard, "
                "escaneie o QR no celular e execute novamente para enviar."
            )
            send_whatsapp = False  # evita o timeout de 20s dentro do pipeline

    pipeline = PulsePipeline(settings)
    try:
        pulse = pipeline.run(
            hours=hours,
            with_llm=with_llm,
            with_tts=with_tts,
            persist=True,
            use_demo=demo,
            send_whatsapp=send_whatsapp,
        )
    except Exception as exc:  # noqa: BLE001 — erro controlado para o cliente MCP
        logger.exception("Falha no pipeline completo via MCP")
        raise ToolError(f"Falha ao executar o pipeline completo: {exc}") from exc

    audio_meta: dict[str, Any] | None = None
    if whatsapp_skip_reason:
        audio_note = whatsapp_skip_reason
        pulse.errors.append(
            f"WHATSAPP_NOT_CONNECTED: instância '{settings.evolution_instance}' "
            f"não está conectada — envio pendente de pareamento."
        )
    elif not send_whatsapp:
        audio_note = "Envio no WhatsApp pulado (send_whatsapp=false)."
    elif not settings.whatsapp_enabled:
        audio_note = (
            "WHATSAPP_ENABLED=false — nenhum envio realizado (configure pulse.env e reinicie a API)."
        )
    elif pulse.audio_path:
        # O pipeline já enviou o texto do boletim; aqui anexamos o áudio.
        ok_audio, audio_meta = wa.send_audio(
            pulse.audio_path, caption="Áudio do boletim DevOps Pulse AI"
        )
        if not ok_audio:
            pulse.errors.append(
                f"WHATSAPP_AUDIO_ERROR: {audio_meta.get('error', 'desconhecido')}"
            )
            audio_note = f"Áudio não enviado: {audio_meta.get('error', 'desconhecido')}"
        else:
            audio_note = f"Áudio anexado: {audio_meta.get('file')}"
    else:
        audio_note = "Sem áudio disponível para anexar (TTS desabilitado ou falhou)."

    if pulse.data_source == "demo":
        audio_note = ((audio_note or "") + " | DADOS DEMO (não são reais).").strip(" |")

    # Status honesto: se o envio no WhatsApp foi pulado/falhou, o pipeline
    # pediu "completo" mas não entregou o envio — marca como parcial.
    if send_whatsapp is False and whatsapp_skip_reason and pulse.status == "success":
        pulse.status = "partial"

    payload: dict[str, Any] = {
        "tool": "run_full_bulletin",
        "status": pulse.status,
        "execution_id": pulse.execution_id,
        "repository": pulse.repository,
        "data_source": pulse.data_source,
        "queried_at": pulse.generated_at,
        "period": {
            "from": pulse.period.from_.isoformat() if pulse.period else None,
            "to": pulse.period.to.isoformat() if pulse.period else None,
        },
        "metrics": pulse.metrics.as_dict(),
        "alerts": [a.model_dump() for a in pulse.alerts],
        "summary_llm": pulse.summary,
        "bulletin": pulse.bulletin,
        "audio_path": pulse.audio_path,
        "whatsapp": pulse.whatsapp,
        "whatsapp_audio": audio_meta,
        "audio_note": audio_note,
        "timings_ms": pulse.timings.model_dump(),
        "errors": pulse.errors,
        "notes": [
            "Pipeline executado de ponta a ponta com persistência no SQLite local.",
            (
                "Dados de DEMONSTRAÇÃO fictícios — não são evidência de produção."
                if pulse.data_source == "demo"
                else "Coleta da API do GitHub (primeira página, até 100 itens por tipo)."
            ),
        ],
    }
    return payload


def create_mcp_http_app() -> Starlette:
    """App Starlette do transporte Streamable HTTP (montado em /mcp pela API)."""
    # Segurança de transporte: aceita apenas hosts locais e origens de navegador
    # locais (página aberta via file:// envia Origin "null"). Nada exposto externamente.
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "localhost",
            "localhost:*",
            "127.0.0.1",
            "127.0.0.1:*",
            "[::1]",
            "[::1]:*",
        ],
        allowed_origins=[
            "null",
            "http://localhost",
            "http://localhost:*",
            "http://127.0.0.1",
            "http://127.0.0.1:*",
        ],
    )
    return mcp.streamable_http_app(
        streamable_http_path="/",
        json_response=True,
        stateless_http=True,
        transport_security=security,
    )


def _redirect_logs_to_stderr() -> None:
    """No transporte stdio, stdout pertence ao protocolo — logs vão para stderr."""
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler) and getattr(handler, "stream", None) is sys.stdout:
            handler.stream = sys.stderr


def main() -> None:
    """Servidor MCP via stdio: ``python -m app.mcp_server``."""
    setup_logging()
    _redirect_logs_to_stderr()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
