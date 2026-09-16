"""Esquemas Pydantic do boletim e de logs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Period(BaseModel):
    from_: datetime = Field(alias="from")
    to: datetime

    model_config = {"populate_by_name": True}


class Metrics(BaseModel):
    commits: int = 0
    issues_opened: int = 0
    issues_closed: int = 0
    pull_requests_opened: int = 0
    pull_requests_closed: int = 0
    stale_pull_requests: int = 0
    open_issues: int = 0
    workflow_runs: int = 0
    workflow_success: int = 0
    workflow_failure: int = 0
    workflow_success_rate: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()


class Alert(BaseModel):
    type: str
    severity: Literal["low", "medium", "high"] = "medium"
    message: str


class StageTimings(BaseModel):
    collection_latency_ms: int = 0
    metrics_latency_ms: int = 0
    llm_latency_ms: int = 0
    tts_latency_ms: int = 0
    persistence_latency_ms: int = 0
    total_pipeline_latency_ms: int = 0


class PulseResponse(BaseModel):
    generated_at: str = Field(default_factory=utc_now_iso)
    execution_id: str = ""
    repository: str = ""
    period: Period
    metrics: Metrics
    alerts: list[Alert] = Field(default_factory=list)
    timings: StageTimings = Field(default_factory=StageTimings)
    collection_latency_ms: int = 0
    status: Literal["success", "partial", "error"] = "success"
    data_source: Literal["github", "demo"] = "github"
    summary: str | None = None
    audio_path: str | None = None
    errors: list[str] = Field(default_factory=list)


class StructuredLog(BaseModel):
    timestamp: str = Field(default_factory=utc_now_iso)
    execution_id: str
    stage: str
    status: str
    duration_ms: int = 0
    message: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)
