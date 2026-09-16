"""Pipeline local: coleta → métricas → alertas → LLM → TTS → persistência."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.alerts import generate_alerts
from app.config import Settings, get_settings
from app.demo_data import build_demo_raw
from app.github_client import GitHubAPIError, GitHubClient
from app.logging_config import get_logger, log_event
from app.metrics import compute_metrics
from app.ollama_client import OllamaClient
from app.persistence import Persistence
from app.schemas import Period, PulseResponse, StageTimings
from app.tts_client import TTSClient

logger = get_logger(__name__)


def new_execution_id(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d-%H%M%S")
    return f"PULSE-{stamp}-{uuid.uuid4().hex[:4].upper()}"


def _ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


class PulsePipeline:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.github = GitHubClient(self.settings)
        self.ollama = OllamaClient(self.settings)
        self.tts = TTSClient(self.settings)
        self.store = Persistence(self.settings)

    def run(
        self,
        *,
        hours: int = 24,
        with_llm: bool = True,
        with_tts: bool = True,
        persist: bool = True,
        use_demo: bool | None = None,
    ) -> PulseResponse:
        started = time.perf_counter()
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=hours)
        window_end = now
        execution_id = new_execution_id(now)
        errors: list[str] = []
        status = "success"
        data_source = "github"

        log_event(logger, execution_id=execution_id, stage="collection", status="COLLECTION_STARTED")

        raw: dict[str, Any]
        t = time.perf_counter()
        demo = self.settings.demo_mode if use_demo is None else use_demo
        try:
            if demo:
                raw = build_demo_raw(window_start, window_end)
                data_source = "demo"
                errors.append("DEMO_MODE=true — dados fictícios, não são evidência de produção.")
                status = "partial"
            else:
                raw = self.github.fetch_raw(window_start=window_start, window_end=window_end)
            collection_ms = _ms(t)
            log_event(
                logger,
                execution_id=execution_id,
                stage="collection",
                status="COLLECTION_SUCCESS",
                duration_ms=collection_ms,
            )
        except GitHubAPIError as exc:
            collection_ms = _ms(t)
            errors.append(f"COLLECTION_ERROR: {exc}")
            status = "error"
            log_event(
                logger,
                execution_id=execution_id,
                stage="collection",
                status="COLLECTION_ERROR",
                duration_ms=collection_ms,
                message=str(exc),
                level="ERROR",
            )
            raw = {"commits": [], "issues": [], "pull_requests": [], "workflow_runs": []}

        t = time.perf_counter()
        metrics = compute_metrics(
            raw,
            window_start=window_start,
            window_end=window_end,
            stale_pr_days=self.settings.stale_pr_days,
        )
        metrics_ms = _ms(t)

        alerts = generate_alerts(
            metrics,
            stale_pr_days=self.settings.stale_pr_days,
            low_ci_success_rate=self.settings.low_ci_success_rate,
            high_issue_volume=self.settings.high_issue_volume,
            unusual_activity_multiplier=self.settings.unusual_activity_multiplier,
        )

        summary: str | None = None
        llm_ms = 0
        tts_ms = 0
        audio_path: str | None = None

        if with_llm:
            log_event(logger, execution_id=execution_id, stage="ollama", status="LLM_STARTED")
            t = time.perf_counter()
            summary, llm_meta = self.ollama.generate_summary(
                metrics, [a.model_dump() for a in alerts]
            )
            llm_ms = _ms(t)
            if llm_meta.get("success"):
                log_event(
                    logger,
                    execution_id=execution_id,
                    stage="ollama",
                    status="LLM_SUCCESS",
                    duration_ms=llm_ms,
                )
            else:
                errors.append(f"LLM_ERROR: {llm_meta.get('error', 'fallback')}")
                status = "partial" if status == "success" else status
                log_event(
                    logger,
                    execution_id=execution_id,
                    stage="ollama",
                    status="LLM_ERROR",
                    duration_ms=llm_ms,
                    message=str(llm_meta.get("error", "")),
                    level="WARNING",
                )

        if with_tts and summary:
            log_event(logger, execution_id=execution_id, stage="tts", status="TTS_STARTED")
            t = time.perf_counter()
            audio_path, tts_meta = self.tts.synthesize(summary, execution_id)
            tts_ms = _ms(t)
            if tts_meta.get("success"):
                log_event(
                    logger,
                    execution_id=execution_id,
                    stage="tts",
                    status="TTS_SUCCESS",
                    duration_ms=tts_ms,
                )
            else:
                errors.append(f"TTS_ERROR: {tts_meta.get('error', 'desconhecido')}")
                status = "partial" if status == "success" else status
                log_event(
                    logger,
                    execution_id=execution_id,
                    stage="tts",
                    status="TTS_ERROR",
                    duration_ms=tts_ms,
                    message=str(tts_meta.get("error", "")),
                    level="WARNING",
                )

        persistence_ms = 0
        pulse = PulseResponse(
            execution_id=execution_id,
            repository=self.settings.repo_full_name or ("demo/devops-pulse" if data_source == "demo" else ""),
            period=Period(**{"from": window_start, "to": window_end}),
            metrics=metrics,
            alerts=alerts,
            collection_latency_ms=collection_ms,
            status=status,
            data_source=data_source,  # type: ignore[arg-type]
            summary=summary,
            audio_path=audio_path,
            errors=errors,
            timings=StageTimings(
                collection_latency_ms=collection_ms,
                metrics_latency_ms=metrics_ms,
                llm_latency_ms=llm_ms,
                tts_latency_ms=tts_ms,
                persistence_latency_ms=0,
                total_pipeline_latency_ms=_ms(started),
            ),
        )

        if persist:
            t = time.perf_counter()
            self.store.init()
            result = self.store.save_execution(pulse)
            persistence_ms = _ms(t)
            if not result.get("success"):
                errors.append(f"PERSISTENCE_ERROR: {result.get('error')}")
                status = "partial" if status == "success" else status
                pulse.status = status
                pulse.errors = errors
                log_event(
                    logger,
                    execution_id=execution_id,
                    stage="persistence",
                    status="PERSISTENCE_ERROR",
                    duration_ms=persistence_ms,
                    message=str(result.get("error", "")),
                    level="WARNING",
                )
            else:
                log_event(
                    logger,
                    execution_id=execution_id,
                    stage="persistence",
                    status="PERSISTENCE_SUCCESS",
                    duration_ms=persistence_ms,
                )

        total_ms = _ms(started)
        pulse.timings = StageTimings(
            collection_latency_ms=collection_ms,
            metrics_latency_ms=metrics_ms,
            llm_latency_ms=llm_ms,
            tts_latency_ms=tts_ms,
            persistence_latency_ms=persistence_ms,
            total_pipeline_latency_ms=total_ms,
        )
        pulse.status = status
        pulse.errors = errors

        if persist and persistence_ms > 0:
            # atualiza timings finais (com persist) no registro já gravado
            try:
                self.store.update_timings(execution_id, pulse.timings)
            except Exception:  # noqa: BLE001 — não derruba o pipeline por causa do update
                logger.debug("Falha ao atualizar timings no SQLite", exc_info=True)

        log_event(
            logger,
            execution_id=execution_id,
            stage="pipeline",
            status="PIPELINE_SUCCESS" if status != "error" else "PIPELINE_ERROR",
            duration_ms=total_ms,
            extra={"status": status},
        )
        return pulse
