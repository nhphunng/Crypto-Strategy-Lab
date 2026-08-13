from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

_BLOCKED_KEYS = {"authorization", "cookie", "password", "secret", "token", "api_key"}


def sanitize_fields(fields: dict[str, Any]) -> dict[str, Any]:
    return {
        key: "[REDACTED]" if key.lower() in _BLOCKED_KEYS else value
        for key, value in fields.items()
    }


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(sanitize_fields(fields))
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    # Dependency INFO records contain full request URLs. A future authenticated
    # provider could place credentials or sensitive selectors in those URLs, so
    # application-owned sanitized provider outcome records are the only HTTP
    # records emitted at normal operating levels.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
