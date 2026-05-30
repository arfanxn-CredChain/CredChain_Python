"""Structured JSON logger configured to mirror Go's zap field shape."""

import json
import logging
import sys
from datetime import UTC, datetime

from app.config import settings


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects.

    Always-present fields: timestamp, level, logger, message.
    Optional fields are merged from `record.extra_fields` if present —
    callers attach them via `logger.info("msg", extra={"extra_fields": {...}})`.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def get_logger(name: str = "credchain_python") -> logging.Logger:
    """Return a logger configured for JSON output to stdout (or to the
    file path in LOG_OUTPUT). Idempotent: subsequent calls with the same
    name return the already-configured instance.
    """
    log = logging.getLogger(name)
    if log.handlers:
        return log

    level = _LEVEL_MAP.get(settings.log_level.lower(), logging.INFO)
    log.setLevel(level)
    log.propagate = False

    if settings.log_output == "stdout":
        handler: logging.Handler = logging.StreamHandler(sys.stdout)
    else:
        handler = logging.FileHandler(settings.log_output)

    handler.setFormatter(JsonFormatter())
    log.addHandler(handler)
    return log
