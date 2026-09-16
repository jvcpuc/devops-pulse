"""Gera relatório consolidado (JSON + Markdown) a partir de data/results/.

Uso:
  python scripts/generate_report.py
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS = PROJECT_ROOT / "data" / "results"


def load_executions(db_path: Path) -> list[dict]:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM executions ORDER BY created_at DESC LIMIT 100").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def main() -> None:
    db = RESULTS / "pulse.db"
    executions = load_executions(db)
    stress_files = sorted(RESULTS.glob("stress_test_*.json"))

    latencies = []
    statuses = {"success": 0, "partial": 0, "error": 0}
    for e in executions:
        statuses[e.get("status", "error")] = statuses.get(e.get("status", "error"), 0) + 1
        try:
            timings = json.loads(e.get("timings_json") or "{}")
            if timings.get("total_pipeline_latency_ms"):
                latencies.append(timings["total_pipeline_latency_ms"])
        except json.JSONDecodeError:
            pass

    total = len(executions)
    success_rate = round((statuses.get("success", 0) / total) * 100, 2) if total else 0.0

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "executions_total": total,
        "status_counts": statuses,
        "success_rate_pct": success_rate,
        "avg_pipeline_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "stress_test_files": [str(p.name) for p in stress_files],
        "note": "ROI e economia exigem premissas documentadas — ver PERFORMANCE.md. Não inventar números.",
    }

    out_json = RESULTS / "report.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Relatório de Performance — DevOps Pulse AI",
        "",
        f"Gerado em: {report['generated_at']}",
        "",
        "## Execuções",
        "",
        f"- Total: {total}",
        f"- Success: {statuses.get('success', 0)}",
        f"- Partial: {statuses.get('partial', 0)}",
        f"- Error: {statuses.get('error', 0)}",
        f"- Taxa de sucesso: {success_rate}%",
        f"- Latência média do pipeline: {report['avg_pipeline_latency_ms']} ms",
        "",
        "## Stress tests",
        "",
    ]
    if stress_files:
        for p in stress_files:
            md.append(f"- `{p.name}`")
    else:
        md.append("- Nenhum stress test executado ainda (`python scripts/stress_test.py`).")
    md.extend(
        [
            "",
            "## Observação ética",
            "",
            "Números acima vêm apenas de execuções reais neste ambiente.",
            "Não apresentar dados de demonstração (`DEMO_MODE`) como produção.",
            "",
        ]
    )
    out_md = RESULTS / "report.md"
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(f"Relatórios em:\n  {out_json}\n  {out_md}")


if __name__ == "__main__":
    main()
