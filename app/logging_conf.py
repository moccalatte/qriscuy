"""Application logging configuration helpers."""
from __future__ import annotations

import json
import logging
from logging.config import dictConfig
from typing import Any

from .config import settings


def _json_formatter(record: logging.LogRecord) -> str:
    payload: dict[str, Any] = {
        "level": record.levelname,
        "logger": record.name,
        "message": record.getMessage(),
    }
    default_keys = {
        "name",
        "msg",
        "message",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "process",
        "processName",
    }
    extra = {k: v for k, v in record.__dict__.items() if k not in default_keys}
    if extra:
        payload.update(extra)
    if record.exc_info:
        payload["exc_info"] = logging.Formatter().formatException(record.exc_info)
    return json.dumps(payload, ensure_ascii=False)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: D401 - overrides base
        return _json_formatter(record)


def configure_logging() -> None:
    """Configure global logging based on settings."""

    log_format = JsonFormatter() if settings.logging.json_logs else logging.Formatter("%(levelname)s %(name)s %(message)s")

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": JsonFormatter if settings.logging.json_logs else logging.Formatter,
                    "fmt": "%(levelname)s %(name)s %(message)s",
                }
            },
            "handlers": {
                "default": {
                    "level": settings.logging.level,
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                }
            },
            "loggers": {
                "": {
                    "handlers": ["default"],
                    "level": settings.logging.level,
                }
            },
        }
    )

    # Apply custom formatter if JSON logging is enabled.
    if settings.logging.json_logs:
        handler = logging.getLogger().handlers[0]
        handler.setFormatter(log_format)
