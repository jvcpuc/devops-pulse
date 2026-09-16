"""Persistência: SQLite por padrão (aceito pelo enunciado) + interface para Sheets."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import Settings
from app.logging_config import get_logger
from app.schemas import PulseResponse, StageTimings

logger = get_logger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT UNIQUE NOT NULL,
    generated_at TEXT NOT NULL,
    repository TEXT,
    status TEXT,
    data_source TEXT,
    metrics_json TEXT,
    alerts_json TEXT,
    timings_json TEXT,
    summary TEXT,
    audio_path TEXT,
    errors_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_exec_created ON executions(created_at);
"""


class Persistence:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.backend = settings.persistence_backend.lower()
        self.db_path: Path = settings.sqlite_abs_path

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        if self.backend != "sqlite":
            logger.info("Backend de persistência=%s (Sheets requer credencial externa)", self.backend)
            return
        with self._connect() as conn:
            conn.executescript(SCHEMA)
        logger.info("SQLite inicializado em %s", self.db_path)

    def save_execution(self, pulse: PulseResponse) -> dict[str, Any]:
        if self.backend != "sqlite":
            return {
                "success": False,
                "error": (
                    f"Backend '{self.backend}' não implementado localmente. "
                    "Configure GOOGLE_SHEET_ID e use n8n para Sheets, ou PERSISTENCE_BACKEND=sqlite."
                ),
            }
        payload = {
            "execution_id": pulse.execution_id,
            "generated_at": pulse.generated_at,
            "repository": pulse.repository,
            "status": pulse.status,
            "data_source": pulse.data_source,
            "metrics_json": json.dumps(pulse.metrics.as_dict(), ensure_ascii=False),
            "alerts_json": json.dumps([a.model_dump() for a in pulse.alerts], ensure_ascii=False),
            "timings_json": json.dumps(pulse.timings.model_dump(), ensure_ascii=False),
            "summary": pulse.summary or "",
            "audio_path": pulse.audio_path or "",
            "errors_json": json.dumps(pulse.errors, ensure_ascii=False),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO executions (
                        execution_id, generated_at, repository, status, data_source,
                        metrics_json, alerts_json, timings_json, summary, audio_path,
                        errors_json, created_at
                    ) VALUES (
                        :execution_id, :generated_at, :repository, :status, :data_source,
                        :metrics_json, :alerts_json, :timings_json, :summary, :audio_path,
                        :errors_json, :created_at
                    )
                    """,
                    payload,
                )
            return {"success": True, "execution_id": pulse.execution_id, "backend": "sqlite"}
        except sqlite3.Error as exc:
            logger.error("Falha ao persistir: %s", exc)
            return {"success": False, "error": str(exc)}

    def update_timings(self, execution_id: str, timings: StageTimings) -> None:
        """Atualiza timings finais (inclui persistência) após o INSERT."""
        if self.backend != "sqlite":
            return
        with self._connect() as conn:
            conn.execute(
                "UPDATE executions SET timings_json = ? WHERE execution_id = ?",
                (json.dumps(timings.model_dump(), ensure_ascii=False), execution_id),
            )

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        if self.backend != "sqlite" or not self.db_path.exists():
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM executions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            for key in ("metrics_json", "alerts_json", "timings_json", "errors_json"):
                if item.get(key):
                    try:
                        item[key.replace("_json", "")] = json.loads(item[key])
                    except json.JSONDecodeError:
                        item[key.replace("_json", "")] = None
            result.append(item)
        return result
