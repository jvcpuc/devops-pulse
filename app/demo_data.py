"""Dados de demonstração rotulados — NÃO são dados reais."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def build_demo_raw(window_start: datetime, window_end: datetime) -> dict[str, Any]:
    """Gera um payload de demonstração com o mesmo formato do GitHub Client.

    ATENÇÃO: valores fictícios para testar o pipeline sem token/API.
    Nunca apresentar estes números como dados reais.
    """
    mid = window_start + (window_end - window_start) / 2
    hour = timedelta(hours=1)
    day = timedelta(days=1)

    commits = [
        {"sha": f"demo{i:02d}", "date": (mid - i * hour).isoformat(), "message": f"commit demo {i}"}
        for i in range(8)
    ]
    issues = [
        {
            "number": 100 + i,
            "title": f"Issue demo {i}",
            "state": "closed" if i < 3 else "open",
            "created_at": (mid - i * hour).isoformat(),
            "closed_at": (mid - i * hour + hour).isoformat() if i < 3 else None,
        }
        for i in range(6)
    ]
    pulls = [
        {
            "number": 200 + i,
            "title": f"PR demo {i}",
            "state": "closed" if i < 2 else "open",
            "created_at": (window_start - (5 - i) * day).isoformat(),
            "closed_at": (mid).isoformat() if i < 2 else None,
            "merged_at": (mid).isoformat() if i < 2 else None,
        }
        for i in range(5)
    ]
    runs = [
        {
            "id": 1000 + i,
            "name": f"ci-demo-{i}",
            "status": "completed",
            "conclusion": "failure" if i in (1, 4) else "success",
            "created_at": (mid - i * hour).isoformat(),
        }
        for i in range(7)
    ]
    return {
        "commits": commits,
        "issues": issues,
        "pull_requests": pulls,
        "workflow_runs": runs,
        "_demo": True,
        "_notice": "DADOS DE DEMONSTRAÇÃO — não usar como evidência de produção.",
    }
