import json
import logging
import os
from datetime import datetime, timezone

import requests


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
UNIFIED_AGENT_URL = os.getenv("UNIFIED_AGENT_URL", "http://158.160.179.91:22132/write")
HTTP_TIMEOUT = float(os.getenv("LOG_HTTP_TIMEOUT", "1.0"))

# Keys present on every LogRecord; used to filter extras for JSON payload.
_RESERVED = {
    "name",
    "msg",
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
    "processName",
    "process",
    "message",
}


class JsonFormatter(logging.Formatter):
    """Render log records as JSON with extras preserved."""

    def format(self, record: logging.LogRecord) -> str:
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _RESERVED and not k.startswith("_")
        }
        payload = {
            "message": record.getMessage(),
            "level": record.levelname,
            "logger": record.name,
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
        }
        if extras:
            payload["extra"] = extras
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class HttpPostHandler(logging.Handler):
    """Send each log record to an HTTP endpoint."""

    def __init__(self, url: str, timeout: float = 1.0):
        super().__init__()
        self.url = url
        self.timeout = timeout

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload = self.format(record)
            headers = {"Content-Type": "application/json"}
            requests.post(self.url, data=payload, headers=headers, timeout=self.timeout)
            print("log requested")
        except Exception:
            self.handleError(record)


def _configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    # Prevent duplicate handlers on reload.
    if any(isinstance(h, HttpPostHandler) for h in root.handlers):
        return

    formatter = JsonFormatter()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    http_handler = HttpPostHandler(UNIFIED_AGENT_URL, timeout=HTTP_TIMEOUT)
    http_handler.setLevel(LOG_LEVEL)
    http_handler.setFormatter(formatter)
    root.addHandler(http_handler)


_configure_logging()
