"""Testes de alertas e thresholds."""

from datetime import datetime, timedelta, timezone

from app.alerts import generate_alerts
from app.metrics import compute_metrics
from app.schemas import Metrics

NOW = datetime(2026, 9, 15, 20, 0, tzinfo=timezone.utc)
START = NOW - timedelta(hours=24)


def _metrics(**kwargs) -> Metrics:
    base = {
        "commits": 1,
        "issues_opened": 1,
        "issues_closed": 0,
        "pull_requests_opened": 1,
        "pull_requests_closed": 0,
        "stale_pull_requests": 0,
        "open_issues": 1,
        "workflow_runs": 2,
        "workflow_success": 2,
        "workflow_failure": 0,
        "workflow_success_rate": 100.0,
    }
    base.update(kwargs)
    return Metrics(**base)


def test_no_alerts_when_healthy():
    alerts = generate_alerts(_metrics())
    assert alerts == []


def test_ci_failure_alert():
    alerts = generate_alerts(_metrics(workflow_failure=2, workflow_success=1, workflow_runs=3, workflow_success_rate=33.3))
    types = {a.type for a in alerts}
    assert "CI_FAILURE" in types
    assert "LOW_CI_SUCCESS_RATE" in types


def test_stale_pr_alert():
    alerts = generate_alerts(_metrics(stale_pull_requests=2), stale_pr_days=3)
    assert any(a.type == "STALE_PR" for a in alerts)


def test_high_issue_volume_threshold():
    alerts = generate_alerts(_metrics(issues_opened=10), high_issue_volume=10)
    assert any(a.type == "HIGH_ISSUE_VOLUME" for a in alerts)
    alerts_low = generate_alerts(_metrics(issues_opened=9), high_issue_volume=10)
    assert not any(a.type == "HIGH_ISSUE_VOLUME" for a in alerts_low)


def test_unusual_activity():
    alerts = generate_alerts(
        _metrics(commits=50, pull_requests_opened=10, issues_opened=5),
        baseline_activity=10,
        unusual_activity_multiplier=2.0,
    )
    assert any(a.type == "UNUSUAL_ACTIVITY" for a in alerts)


def test_alerts_from_raw_pipeline_shape():
    raw = {
        "commits": [{"date": (NOW - timedelta(hours=1)).isoformat()}],
        "issues": [],
        "pull_requests": [
            {"created_at": (NOW - timedelta(days=10)).isoformat(), "closed_at": None}
        ],
        "workflow_runs": [
            {"conclusion": "failure", "created_at": (NOW - timedelta(hours=1)).isoformat()}
        ],
    }
    m = compute_metrics(raw, window_start=START, window_end=NOW, stale_pr_days=3)
    alerts = generate_alerts(m, stale_pr_days=3, low_ci_success_rate=80)
    types = {a.type for a in alerts}
    assert "STALE_PR" in types
    assert "CI_FAILURE" in types
