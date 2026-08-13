import json
import logging
from datetime import datetime, timezone

from src.config.config import settings

_IS_GCP = settings.is_gcp
_LOG_LEVEL = settings.log_level.upper()

_SEVERITY_MAP = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
}

_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_LOCAL_FORMAT = "[%(asctime)s] %(levelname)-8s : %(name)s - %(message)s"


class _GcpJsonFormatter(logging.Formatter):
    """
    JSON formatter compatible with GCP Cloud Logging structured logs.

    GCP Cloud Logging parses 'severity', 'message', and 'time' fields
    to display logs with proper severity filtering in the console.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON compatible with GCP Cloud Logging."""
        payload: dict = {
            "severity": _SEVERITY_MAP.get(record.levelno, "DEFAULT"),
            "message": record.getMessage(),
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "logger": record.name,
            "logging.googleapis.com/sourceLocation": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            },
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _configure_root_logger() -> None:
    """Configure the root logger once for local or GCP logging."""
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler()
    if _IS_GCP:
        handler.setFormatter(_GcpJsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(fmt=_LOCAL_FORMAT, datefmt=_DATE_FORMAT))

    root.setLevel(_LOG_LEVEL)
    root.addHandler(handler)


_configure_root_logger()


def configure_uvicorn_loggers() -> None:
    """
    Override Uvicorn loggers to use the root logger's format.

    Call this in the FastAPI lifespan startup to unify log format
    between Uvicorn and application loggers.
    """
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True

    # Suppress verbose httpx/httpcore INFO logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the given name."""
    return logging.getLogger(name)
