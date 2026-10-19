"""Núcleo do teste de estresse do microsserviço (reutilizado pelo CLI e pelo MCP).

Envia lotes de requisições GET contra os endpoints do próprio DevOps Pulse AI
(`/health`, `/api/pulse`, `/api/pipeline/run`), medindo latência e taxa de sucesso.

Limites de segurança: apenas endpoints locais whitelisted — nenhuma URL arbitrária.
"""

from __future__ import annotations

import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import urlparse

import httpx

# Endpoints permitidos (whitelist): apenas rotas do próprio microsserviço.
ALLOWED_ENDPOINTS = ("/health", "/api/pulse", "/api/pipeline/run")

DEFAULT_BASE_URL = "http://127.0.0.1:8000"

# Limites por chamada (evita saturar a máquina na demonstração).
MAX_BATCH_REQUESTS = 50
MAX_TOTAL_REQUESTS = 150
MAX_CONCURRENCY = 20


def validate_target(endpoint: str, base_url: str = DEFAULT_BASE_URL) -> tuple[str, str]:
    """Valida endpoint (whitelist) e base_url (apenas localhost)."""
    endpoint = (endpoint or "").strip()
    if endpoint not in ALLOWED_ENDPOINTS:
        raise ValueError(
            f"Endpoint não permitido: {endpoint!r}. Use um de: {', '.join(ALLOWED_ENDPOINTS)}."
        )
    base_url = (base_url or "").strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError(
            f"base_url inválida: {base_url!r}. O teste de estresse só acessa o "
            "microsserviço local (http://127.0.0.1 ou http://localhost)."
        )
    return endpoint, base_url


def parse_requests(spec: str | list[int | str]) -> list[int]:
    """Interpreta '5,10,25' (ou lista) em lotes de requisições, com limites."""
    if isinstance(spec, str):
        parts = [p.strip() for p in spec.split(",") if p.strip()]
    else:
        parts = [str(p).strip() for p in spec]
    try:
        counts = [int(p) for p in parts]
    except ValueError as exc:
        raise ValueError(f"Lista de requisições inválida: {spec!r} (use ex.: '5,10').") from exc
    if not counts:
        raise ValueError("Informe ao menos um lote de requisições (ex.: '5,10').")
    if len(counts) > 3:
        raise ValueError("Máximo de 3 lotes por execução (ex.: '5,10,25').")
    if any(c < 1 or c > MAX_BATCH_REQUESTS for c in counts):
        raise ValueError(f"Cada lote deve ter entre 1 e {MAX_BATCH_REQUESTS} requisições.")
    if sum(counts) > MAX_TOTAL_REQUESTS:
        raise ValueError(f"Total limitado a {MAX_TOTAL_REQUESTS} requisições por execução.")
    return counts


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


def one_request(base_url: str, endpoint: str, timeout: float) -> dict[str, Any]:
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


def run_batch(n: int, base_url: str, endpoint: str, concurrency: int, timeout: float) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
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
        "p95_latency_ms": round(percentile(latencies, 95), 2) if len(latencies) >= 2 else (
            round(latencies[0], 2) if latencies else None
        ),
        "requests_per_second": round(n / wall, 2) if wall > 0 else None,
        "sample_errors": [r["error"] for r in results if r["error"]][:3],
    }


def run_stress(
    requests: str | list[int | str] = "5,10",
    concurrency: int = 3,
    endpoint: str = "/api/pulse",
    base_url: str = DEFAULT_BASE_URL,
    timeout_s: float = 30.0,
) -> dict[str, Any]:
    """Executa os lotes e devolve o relatório consolidado (mesmo formato do CLI)."""
    endpoint, base_url = validate_target(endpoint, base_url)
    counts = parse_requests(requests)
    concurrency = max(1, min(int(concurrency), MAX_CONCURRENCY))
    timeout = max(1.0, min(float(timeout_s), 60.0))

    batches: list[dict[str, Any]] = []
    for n in counts:
        batches.append(run_batch(n, base_url, endpoint, concurrency, timeout))

    total_requests = sum(b["requests"] for b in batches)
    total_success = sum(b["success"] for b in batches)
    return {
        "base_url": base_url,
        "endpoint": endpoint,
        "concurrency": concurrency,
        "batches": batches,
        "total_requests": total_requests,
        "total_success": total_success,
        "overall_success_rate": round((total_success / total_requests) * 100, 2)
        if total_requests
        else 0.0,
    }
