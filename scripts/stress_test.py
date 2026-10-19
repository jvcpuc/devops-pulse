"""Teste de stress do endpoint /api/pulse (ou /api/pipeline/run).

Uso:
  python scripts/stress_test.py --requests 10
  python scripts/stress_test.py --requests 10,25,50,100 --endpoint /api/pulse

A lógica de medição mora em app/stress.py (compartilhada com a ferramenta MCP
run_stress_test); aqui ficam apenas a linha de comando e a gravação do relatório.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # permite `python scripts/stress_test.py`

from app.stress import run_stress  # noqa: E402

RESULTS_DIR = PROJECT_ROOT / "data" / "results"


def main() -> None:
    parser = argparse.ArgumentParser(description="Stress test DevOps Pulse AI")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--endpoint", default="/api/pulse")
    parser.add_argument("--requests", default="10,25,50,100")
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    report_time = datetime.now(timezone.utc).isoformat()
    try:
        result = run_stress(
            requests=args.requests,
            concurrency=args.concurrency,
            endpoint=args.endpoint,
            base_url=args.base_url,
            timeout_s=args.timeout,
        )
    except ValueError as exc:
        print(f"Parâmetros inválidos: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    report = {"generated_at": report_time, **result}
    for batch in report["batches"]:
        print(
            f"→ {batch['requests']} requisições em {batch['endpoint']} "
            f"(concorrência={batch['concurrency']})..."
        )
        print(
            f"  success={batch['success']}/{batch['requests']} "
            f"p95={batch['p95_latency_ms']}ms rps={batch['requests_per_second']}"
        )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out = RESULTS_DIR / f"stress_test_{stamp}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRelatório salvo em: {out}")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
