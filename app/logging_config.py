"""Logging estruturado em JSON + arquivo."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT, get_settings

LOG_DIR = PROJECT_ROOT / "logs"
_configured = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "execution_id"):
            payload["execution_id"] = record.execution_id
        if hasattr(record, "stage"):
            payload["stage"] = record.stage
        if hasattr(record, "duration_ms"):
            payload["duration_ms"] = record.duration_ms
        if hasattr(record, "status"):
            payload["status"] = record.status
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    global _configured
    if _configured:
        return
    settings = get_settings()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.handlers.clear()
    root.addHandler(handler)

    file_handler = logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")
    file_handler.setFormatter(JsonFormatter())
    root.addHandler(file_handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)


def log_event(
    logger: logging.Logger,
    *,
    execution_id: str,
    stage: str,
    status: str,
    duration_ms: int = 0,
    message: str = "",
    level: str = "INFO",
    **extra: Any,
) -> None:
    getattr(logger, level.lower(), logger.info)(
        message or f"{stage}:{status}",
        extra={
            "execution_id": execution_id,
            "stage": stage,
            "status": status,
            "duration_ms": duration_ms,
            **extra,
        },
    )
