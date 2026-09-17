"""Envia boletim WhatsApp completo no formato da demo (repo n8n-io/n8n)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
GROUP = "120363412036540372@g.us"
APIKEY = "devops-pulse-evolution-key-2026"
BASE = "http://127.0.0.1:8080"


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    pulse = get_json("http://127.0.0.1:8000/api/pulse?hours=24")
    m = pulse.get("metrics") or {}
    t = pulse.get("timings") or {}
    alerts = pulse.get("alerts") or []
    # Prefer open_issues; fall back to issues_opened if needed
    issues_abertas = m.get("open_issues")
    if issues_abertas is None:
        issues_abertas = m.get("issues_opened", 0)

    alert_lines = []
    for a in alerts:
        sev = a.get("severity", "medium")
        msg = a.get("message", a.get("type", ""))
        alert_lines.append(f"• [{sev}] {msg}")
    if not alert_lines:
        alert_lines = ["• Nenhum alerta no período"]

    text = (
        f"[DevOps Pulse AI] Boletim - {pulse.get('execution_id')}\n"
        f"\n"
        f"Repo: {pulse.get('repository')}\n"
        f"Fonte: {pulse.get('data_source')} | Status: {pulse.get('status')}\n"
        f"\n"
        f"Indicadores (24h):\n"
        f". Commits: {m.get('commits', 0)}\n"
        f". PRs abertos: {m.get('pull_requests_opened', 0)} | fechados: {m.get('pull_requests_closed', 0)}\n"
        f". Issues abertas: {issues_abertas}\n"
        f". CI success rate: {m.get('workflow_success_rate', 0)}%\n"
        f". Latência coleta: {t.get('collection_latency_ms', 0)} ms\n"
        f"\n"
        f"Alertas:\n"
        + "\n".join(alert_lines)
        + "\n\n"
        f"Stress test (10/25/50 req): 100% sucesso • p95 ~6,6s\n"
        f"• Pipeline: GitHub → metrics → alerts → n8n"
    )

    (EV / "whatsapp-boletim.txt").write_text(text, encoding="utf-8")

    body = json.dumps({"number": GROUP, "text": text}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/message/sendText/devops-pulse",
        data=body,
        headers={
            "apikey": APIKEY,
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    (EV / "whatsapp-send.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("ENVIADO")
    print(text)
    print("---")
    print("key=", (result.get("key") or {}).get("id"))
    print("status=", result.get("status"))


if __name__ == "__main__":
    main()
