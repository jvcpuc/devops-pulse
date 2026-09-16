"""Teste de stress do endpoint /api/pulse (ou /api/pipeline/run).

Uso:
  python scripts/stress_test.py --requests 10
  python scripts/stress_test.py --requests 10,25,50,100 --endpoint /api/pulse
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "data" / "results"


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * (pct / 100.0)
    floor = int(k)
    ceil = min(floor + 1, len(ordered) - 1)
    if floor == ceil:
        return ordered[floor]
    return ordered[floor] + (ordered[ceil] - ordered[floor]) * (k - floor)


def one_request(base_url: str, endpoint: str, timeout: float) -> dict:
    start = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(f"{base_url.rstrip('/')}{endpoint}")
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "ok": resp.status_code == 200,
            "status_code": resp.status_code,
            "latency_ms": latency_ms,
            "error": None if resp.status_code == 200 else resp.text[:200],
        }
    except httpx.HTTPError as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "ok": False,
            "status_code": None,
            "latency_ms": latency_ms,
            "error": str(exc),
        }


def run_batch(n: int, base_url: str, endpoint: str, concurrency: int, timeout: float) -> dict:
    results: list[dict] = []
    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [
            pool.submit(one_request, base_url, endpoint, timeout) for _ in range(n)
        ]
        for fut in as_completed(futures):
            results.append(fut.result())
    wall = time.perf_counter() - wall_start

    latencies = [r["latency_ms"] for r in results if r["ok"]]
    success = sum(1 for r in results if r["ok"])
    errors = n - success

    return {
        "requests": n,
        "concurrency": concurrency,
        "endpoint": endpoint,
        "success": success,
        "errors": errors,
        "success_rate": round((success / n) * 100, 2) if n else 0.0,
        "total_time_s": round(wall, 3),
        "average_latency_ms": round(statistics.mean(latencies), 2) if latencies else None,
        "min_latency_ms": round(min(latencies), 2) if latencies else None,
        "max_latency_ms": round(max(latencies), 2) if latencies else None,
        "p50_latency_ms": round(percentile(latencies, 50), 2) if latencies else None,
        "p95_latency_ms": round(percentile(latencies, 95), 2) if latencies else None,
        "requests_per_second": round(n / wall, 2) if wall > 0 else None,
        "sample_errors": [r["error"] for r in results if r["error"]][:3],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stress test DevOps Pulse AI")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--endpoint", default="/api/pulse")
    parser.add_argument("--requests", default="10,25,50,100")
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    counts = [int(x.strip()) for x in args.requests.split(",") if x.strip()]
    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "endpoint": args.endpoint,
        "batches": [],
    }

    for n in counts:
        print(f"→ {n} requisições em {args.endpoint} (concorrência={args.concurrency})...")
        batch = run_batch(n, args.base_url, args.endpoint, args.concurrency, args.timeout)
        report["batches"].append(batch)
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
