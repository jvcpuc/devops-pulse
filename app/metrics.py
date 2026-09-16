"""Cálculo de indicadores a partir de dados brutos normalizados."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.schemas import Metrics


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def count_in_window(
    items: list[dict[str, Any]],
    date_field: str,
    window_start: datetime,
    window_end: datetime,
) -> int:
    count = 0
    for item in items:
        dt = _parse_dt(item.get(date_field))
        if dt and window_start <= dt <= window_end:
            count += 1
    return count


def success_rate(success: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((success / total) * 100.0, 2)


def compute_metrics(
    raw: dict[str, Any],
    *,
    window_start: datetime,
    window_end: datetime,
    stale_pr_days: int = 3,
) -> Metrics:
    commits = raw.get("commits") or []
    issues = raw.get("issues") or []
    pulls = raw.get("pull_requests") or []
    runs = raw.get("workflow_runs") or []

    commits_in_window = count_in_window(commits, "date", window_start, window_end)

    issues_opened = count_in_window(issues, "created_at", window_start, window_end)
    issues_closed = count_in_window(issues, "closed_at", window_start, window_end)
    open_issues = sum(1 for i in issues if not i.get("closed_at"))

    prs_opened = count_in_window(pulls, "created_at", window_start, window_end)
    prs_closed = count_in_window(pulls, "closed_at", window_start, window_end)

    stale_cutoff = window_end - timedelta(days=stale_pr_days)
    stale_prs = 0
    for pr in pulls:
        if pr.get("closed_at"):
            continue
        created = _parse_dt(pr.get("created_at"))
        if created and created < stale_cutoff:
            stale_prs += 1

    runs_in_window: list[dict[str, Any]] = []
    for run in runs:
        dt = _parse_dt(run.get("created_at") or run.get("run_started_at"))
        if dt and window_start <= dt <= window_end:
            runs_in_window.append(run)

    wf_total = len(runs_in_window)
    wf_success = sum(1 for r in runs_in_window if r.get("conclusion") == "success")
    wf_failure = sum(
        1 for r in runs_in_window if r.get("conclusion") in {"failure", "timed_out", "cancelled"}
    )

    return Metrics(
        commits=commits_in_window,
        issues_opened=issues_opened,
        issues_closed=issues_closed,
        pull_requests_opened=prs_opened,
        pull_requests_closed=prs_closed,
        stale_pull_requests=stale_prs,
        open_issues=open_issues,
        workflow_runs=wf_total,
        workflow_success=wf_success,
        workflow_failure=wf_failure,
        workflow_success_rate=success_rate(wf_success, wf_total),
    )
