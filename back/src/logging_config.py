import json
import logging
import os
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
UNIFIED_AGENT_URL = os.getenv("UNIFIED_AGENT_URL", "http://localhost")
HTTP_TIMEOUT = float(os.getenv("LOG_HTTP_TIMEOUT", "1.0"))
CELERY_LOG_GROUP = os.getenv("CELERY_LOG_GROUP", "")

# Keys present on every LogRecord; used to filter extras for JSON payload
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

    def convert_level(self, level: str) -> str:
        """Yandex log groups use different names for log levels, so this function does the conversion."""
        if level == "NOTSET":
            return "TRACE"
        elif level == "WARNING":
            return "WARN"
        elif level == "CRITICAL":
            return "FATAL"
        else:
            return level


    def format(self, record: logging.LogRecord) -> str:
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _RESERVED and not k.startswith("_")
        }
        payload = {
            "message": record.getMessage(),
            "level": self.convert_level(record.levelname),
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
            headers = {"Content-Type": "application/json", "log-group": CELERY_LOG_GROUP}
            requests.post(self.url, data=payload, headers=headers, timeout=self.timeout)
            print("log requested")
        except Exception:
            self.handleError(record)


def configure_logging(logger: logging.Logger):
    logger.setLevel(logging.INFO)

    formatter = JsonFormatter()

    http_handler = HttpPostHandler(UNIFIED_AGENT_URL, timeout=HTTP_TIMEOUT)
    http_handler.setLevel(LOG_LEVEL)
    http_handler.setFormatter(formatter)
    logger.addHandler(http_handler)
