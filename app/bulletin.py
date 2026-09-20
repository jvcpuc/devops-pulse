"""Formatador do boletim operacional (WhatsApp + versões faladas TTS)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.schemas import Alert, Metrics


def _metrics_dict(metrics: Metrics | dict[str, Any]) -> dict[str, Any]:
    return metrics.as_dict() if hasattr(metrics, "as_dict") else dict(metrics)


def _alerts_dicts(alerts: list[Alert] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for a in alerts:
        out.append(a.model_dump() if hasattr(a, "model_dump") else dict(a))
    return out


def format_bulletin(
    *,
    execution_id: str,
    repository: str,
    data_source: str,
    status: str,
    metrics: Metrics | dict[str, Any],
    alerts: list[Alert] | list[dict[str, Any]],
    collection_latency_ms: int = 0,
    summary: str | None = None,
) -> str:
    """Texto completo enviado ao WhatsApp (formato da demo)."""
    m = _metrics_dict(metrics)
    issues_abertas = m.get("open_issues")
    if issues_abertas is None:
        issues_abertas = m.get("issues_opened", 0)

    alert_lines: list[str] = []
    for d in _alerts_dicts(alerts):
        sev = d.get("severity", "medium")
        msg = d.get("message") or d.get("type") or ""
        alert_lines.append(f"• [{sev}] {msg}")
    if not alert_lines:
        alert_lines = ["• Nenhum alerta no período"]

    parts = [
        f"[DevOps Pulse AI] Boletim - {execution_id}",
        "",
        f"Repo: {repository}",
        f"Fonte: {data_source} | Status: {status}",
        "",
        "Indicadores (24h):",
        f". Commits: {m.get('commits', 0)}",
        f". PRs abertos: {m.get('pull_requests_opened', 0)} | fechados: {m.get('pull_requests_closed', 0)}",
        f". Issues abertas: {issues_abertas}",
        f". CI success rate: {m.get('workflow_success_rate', 0)}%",
        f". Latência coleta: {collection_latency_ms} ms",
        "",
        "Alertas:",
        "\n".join(alert_lines),
        "",
        "Stress test (10/25/50 req): 100% sucesso • p95 ~6,6s",
        "• Pipeline: GitHub → metrics → alerts → TTS → SQLite → WhatsApp",
    ]
    if summary:
        short = " ".join(str(summary).split())[:280]
        parts.extend(["", f"Resumo LLM: {short}"])
    return "\n".join(parts)


def _spoken_repo(repository: str, kokoro: bool = False) -> str:
    r = repository or "repositório"
    # n8n-io / n8n.io → fonética estável em pt-BR
    r = r.replace("n8n-io", "ene oito ene ponto i o")
    r = r.replace("N8N-IO", "ene oito ene ponto i o")
    r = r.replace("n8n.io", "ene oito ene ponto i o")
    r = r.replace("n8n", "ene oito ene")
    r = r.replace("N8N", "ene oito ene")
    r = r.replace("/", " barra ")
    r = r.replace("-", " ")
    return " ".join(r.split())


def _spoken_alert(text: str, kokoro: bool = False) -> str:
    t = (text or "").strip()
    # Edge (Antonio): fonética inglesa legível; Kokoro: português reforçado
    pr = "puli riquéstes" if kokoro else "púl riquêsts"
    repl = [
        ("pull request(s)", pr),
        ("pull requests", pr),
        ("pull request", pr),
        ("PRs", pr),
        ("CI/CD", "integração contínua"),
        ("%", " por cento"),
        ("aberto(s)", "abertos"),
        ("fechado(s)", "fechados"),
        ("n8n-io", "ene oito ene ponto i o"),
        ("n8n", "ene oito ene"),
    ]
    if kokoro:
        repl.append((" GitHub", " Guit-Hub"))
    for a, b in repl:
        t = t.replace(a, b)
    t = t.replace(".0 por cento", " por cento")
    t = " ".join(t.split())
    while t.endswith(".."):
        t = t[:-1]
    return t.strip()


def _pct(value: Any) -> str:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(f - round(f)) < 0.05:
        return str(int(round(f)))
    return f"{f:.1f}".replace(".", " vírgula ")


def _ms_spoken(ms: int) -> str:
    try:
        v = int(ms)
    except (TypeError, ValueError):
        return "0 milissegundos"
    if v >= 1000:
        sec = v / 1000.0
        return f"{sec:.1f}".replace(".", " vírgula ") + " segundos"
    return f"{v} milissegundos"


def format_spoken_bulletin(
    *,
    execution_id: str,
    repository: str,
    data_source: str,
    status: str,
    metrics: Metrics | dict[str, Any],
    alerts: list[Alert] | list[dict[str, Any]],
    collection_latency_ms: int = 0,
    engine: str = "edge",
) -> str:
    """Versão falada do boletim.

    engine='edge'  → termos técnicos naturais (Antonio neural).
    engine='kokoro' → fonética pt-BR reforçada (Kokoro local).
    """
    m = _metrics_dict(metrics)
    issues_abertas = m.get("open_issues")
    if issues_abertas is None:
        issues_abertas = m.get("issues_opened", 0)

    kokoro = engine == "kokoro"
    repo = _spoken_repo(repository or "repositório", kokoro=kokoro)
    if kokoro:
        src = "Guit-Hub" if data_source == "github" else "modo demo"
        st = "sucesso" if status == "success" else str(status)
        pr_word = "puli riquéstes"
        commit_word = "comítes"
        issue_word = "íxues"
        ci_label = "integração contínua"
        exec_line = "Execução registrada no histórico."
        repo_line = f"Repositório {repo}."
    else:
        src = "GitHub" if data_source == "github" else "modo demo"
        st = "sucesso" if status == "success" else str(status)
        pr_word = "púl riquêsts"
        commit_word = "commits"
        issue_word = "issues"
        ci_label = "integração contínua"
        exec_line = "Boletim DevOps Pulse AI."
        repo_line = f"Repositório {repo}."

    alert_parts = []
    for d in _alerts_dicts(alerts):
        msg = d.get("message") or d.get("type") or ""
        if not msg:
            continue
        alert_parts.append(_spoken_alert(msg, kokoro=kokoro))
    if not alert_parts:
        alert_text = "Nenhum alerta no período."
    else:
        alert_text = " ".join(f"Alerta: {p}." for p in alert_parts[:3])

    ci = _pct(m.get("workflow_success_rate", 0))
    lat = _ms_spoken(collection_latency_ms)

    text = (
        f"{exec_line} "
        f"{repo_line} "
        f"Fonte {src}. Status {st}. "
        f"Indicadores das últimas vinte e quatro horas: "
        f"{m.get('commits', 0)} {commit_word}. "
        f"{m.get('pull_requests_opened', 0)} {pr_word} abertos e "
        f"{m.get('pull_requests_closed', 0)} fechados. "
        f"{issues_abertas} {issue_word} abertas. "
        f"Taxa de sucesso de {ci_label} em {ci} por cento. "
        f"Latência de coleta de {lat}. "
        f"{alert_text} "
        f"Fim do boletim."
    )
    return text
