"""API HTTP do DevOps Pulse AI.

Endpoints:
- GET  /health
- GET  /api/pulse          — apenas coleta + métricas + alertas
- POST /api/pipeline/run   — pipeline completo (LLM/TTS/persist opcional)
- GET  /api/executions     — histórico SQLite
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.alerts import generate_alerts
from app.config import get_settings
from app.demo_data import build_demo_raw
from app.github_client import GitHubAPIError, GitHubClient
from app.health import build_health
from app.logging_config import get_logger, setup_logging
from app.metrics import compute_metrics
from app.persistence import Persistence
from app.pipeline import PulsePipeline, new_execution_id
from app.schemas import Period, PulseResponse, StageTimings
from datetime import datetime, timedelta, timezone
import time

setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="DevOps Pulse AI",
    version=__version__,
    description="Microsserviço de coleta, indicadores e boletim de operações de desenvolvimento.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = get_settings()


@app.get("/health")
def health() -> dict[str, Any]:
    return build_health(settings)


@app.get("/api/pulse", response_model=PulseResponse)
def api_pulse(hours: int = Query(24, ge=1, le=168)) -> PulseResponse:
    """Coleta + métricas + alertas (sem LLM/TTS)."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=hours)
    window_end = now
    execution_id = new_execution_id(now)
    t0 = time.perf_counter()
    errors: list[str] = []
    data_source = "github"
    status = "success"

    client = GitHubClient(settings)
    try:
        if settings.demo_mode:
            raw = build_demo_raw(window_start, window_end)
            data_source = "demo"
            errors.append("DEMO_MODE=true — dados de demonstração.")
            status = "partial"
        else:
            raw = client.fetch_raw(window_start=window_start, window_end=window_end)
    except GitHubAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    collection_ms = int((time.perf_counter() - t0) * 1000)
    metrics = compute_metrics(
        raw,
        window_start=window_start,
        window_end=window_end,
        stale_pr_days=settings.stale_pr_days,
    )
    alerts = generate_alerts(
        metrics,
        stale_pr_days=settings.stale_pr_days,
        low_ci_success_rate=settings.low_ci_success_rate,
        high_issue_volume=settings.high_issue_volume,
        unusual_activity_multiplier=settings.unusual_activity_multiplier,
    )

    return PulseResponse(
        execution_id=execution_id,
        repository=settings.repo_full_name or "demo/devops-pulse",
        period=Period(**{"from": window_start, "to": window_end}),
        metrics=metrics,
        alerts=alerts,
        collection_latency_ms=collection_ms,
        status=status,
        data_source=data_source,  # type: ignore[arg-type]
        errors=errors,
        timings=StageTimings(collection_latency_ms=collection_ms, total_pipeline_latency_ms=collection_ms),
    )


class PipelineRunRequest(dict):
    """Modelo leve via query/body flexível."""


@app.post("/api/pipeline/run", response_model=PulseResponse)
def api_pipeline_run(
    hours: int = Query(24, ge=1, le=168),
    with_llm: bool = Query(True),
    with_tts: bool = Query(True),
    persist: bool = Query(True),
) -> PulseResponse:
    pipeline = PulsePipeline(settings)
    try:
        return pipeline.run(hours=hours, with_llm=with_llm, with_tts=with_tts, persist=persist)
    except Exception as exc:  # noqa: BLE001 — último recurso na borda HTTP
        logger.exception("Falha no pipeline")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/executions")
def api_executions(limit: int = Query(20, ge=1, le=200)) -> dict[str, Any]:
    store = Persistence(settings)
    return {"items": store.list_recent(limit=limit)}
