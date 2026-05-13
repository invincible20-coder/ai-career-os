"""
Structured logging configuration.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from backend.core.config import get_settings

_INITIALISED = False

_RESERVED_RECORD_KEYS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


class JsonFormatter(logging.Formatter):
    """Render log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in _RESERVED_RECORD_KEYS or key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level_name: str) -> None:
    """Configure the backend logger once."""

    global _INITIALISED

    root_logger = logging.getLogger("backend")
    level = getattr(logging, level_name.upper(), logging.INFO)

    if _INITIALISED:
        root_logger.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
    root_logger.propagate = False

    _INITIALISED = True


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a backend-scoped logger."""

    if not _INITIALISED:
        configure_logging(get_settings().log_level)
    if not name:
        return logging.getLogger("backend")
    if name.startswith("backend"):
        return logging.getLogger(name)
    return logging.getLogger(f"backend.{name}")
