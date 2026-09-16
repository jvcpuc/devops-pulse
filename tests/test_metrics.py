"""Testes de cálculo de métricas."""

from datetime import datetime, timedelta, timezone

from app.metrics import compute_metrics, count_in_window, success_rate

NOW = datetime(2026, 9, 15, 20, 0, tzinfo=timezone.utc)
START = NOW - timedelta(hours=24)


def test_success_rate_basic():
    assert success_rate(8, 10) == 80.0
    assert success_rate(0, 0) == 0.0
    assert success_rate(5, 5) == 100.0


def test_count_in_window():
    items = [
        {"date": (NOW - timedelta(hours=1)).isoformat()},
        {"date": (NOW - timedelta(hours=48)).isoformat()},
        {"date": None},
    ]
    assert count_in_window(items, "date", START, NOW) == 1


def test_compute_metrics_counts():
    raw = {
        "commits": [
            {"date": (NOW - timedelta(hours=2)).isoformat()},
            {"date": (NOW - timedelta(hours=2)).isoformat()},
        ],
        "issues": [
            {
                "created_at": (NOW - timedelta(hours=3)).isoformat(),
                "closed_at": (NOW - timedelta(hours=1)).isoformat(),
            },
            {"created_at": (NOW - timedelta(hours=5)).isoformat(), "closed_at": None},
        ],
        "pull_requests": [
            {
                "created_at": (NOW - timedelta(days=5)).isoformat(),
                "closed_at": None,
            },
            {
                "created_at": (NOW - timedelta(hours=4)).isoformat(),
                "closed_at": None,
            },
            {
                "created_at": (NOW - timedelta(hours=2)).isoformat(),
                "closed_at": (NOW - timedelta(hours=1)).isoformat(),
            },
        ],
        "workflow_runs": [
            {"conclusion": "success", "created_at": (NOW - timedelta(hours=1)).isoformat()},
            {"conclusion": "failure", "created_at": (NOW - timedelta(hours=2)).isoformat()},
            {"conclusion": "success", "created_at": (NOW - timedelta(hours=3)).isoformat()},
        ],
    }
    m = compute_metrics(raw, window_start=START, window_end=NOW, stale_pr_days=3)
    assert m.commits == 2
    assert m.issues_opened == 2
    assert m.issues_closed == 1
    assert m.open_issues == 1
    assert m.pull_requests_opened == 2
    assert m.pull_requests_closed == 1
    assert m.stale_pull_requests == 1
    assert m.workflow_runs == 3
    assert m.workflow_success == 2
    assert m.workflow_failure == 1
    assert m.workflow_success_rate == success_rate(2, 3)


def test_compute_metrics_empty():
    m = compute_metrics({}, window_start=START, window_end=NOW)
    assert m.commits == 0
    assert m.workflow_success_rate == 0.0


def test_missing_dates_ignored():
    raw = {
        "commits": [{"date": None}, {"date": "not-a-date"}],
        "issues": [{}],
        "pull_requests": [{}],
        "workflow_runs": [{"conclusion": "success", "created_at": None}],
    }
    m = compute_metrics(raw, window_start=START, window_end=NOW)
    assert m.commits == 0
    assert m.workflow_runs == 0
