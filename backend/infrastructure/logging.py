"""Structured logging with correlation and workflow context propagation."""

from contextvars import ContextVar, Token
from datetime import UTC, datetime
import json
import logging
import sys
from typing import Any

_correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_workflow_id_var: ContextVar[str | None] = ContextVar("workflow_id", default=None)

_STANDARD_RECORD_ATTRS = frozenset(
    {
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
        "taskName",
        "thread",
        "threadName",
    }
)


def get_correlation_id() -> str | None:
    """Return the active correlation ID from async context."""
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: str | None) -> Token[str | None]:
    """Bind a correlation ID to the current async context."""
    return _correlation_id_var.set(correlation_id)


def get_workflow_id() -> str | None:
    """Return the active workflow ID from async context."""
    return _workflow_id_var.get()


def set_workflow_id(workflow_id: str | None) -> Token[str | None]:
    """Bind a workflow ID to the current async context."""
    return _workflow_id_var.set(workflow_id)


def reset_correlation_id(token: Token[str | None]) -> None:
    """Reset the correlation ID context variable using its token."""
    _correlation_id_var.reset(token)


def reset_workflow_id(token: Token[str | None]) -> None:
    """Reset the workflow ID context variable using its token."""
    _workflow_id_var.reset(token)


class ContextFilter(logging.Filter):
    """Inject correlation_id and workflow_id onto every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = getattr(record, "correlation_id", None) or get_correlation_id()
        record.workflow_id = getattr(record, "workflow_id", None) or get_workflow_id()
        return True


class StructuredJsonFormatter(logging.Formatter):
    """Format log records as single-line JSON payloads."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
            "workflow_id": getattr(record, "workflow_id", None),
        }

        for key, value in record.__dict__.items():
            if (
                key not in _STANDARD_RECORD_ATTRS
                and key not in payload
                and not key.startswith("_")
            ):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(payload, default=str)


class StructuredTextFormatter(logging.Formatter):
    """Human-readable log formatter including correlation and workflow context."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=UTC).strftime("%Y-%m-%d %H:%M:%S")
        corr = getattr(record, "correlation_id", None) or "-"
        wf = getattr(record, "workflow_id", None) or "-"
        base = (
            f"{ts} | {record.levelname:<8} | {record.name} | "
            f"corr={corr} wf={wf} | {record.getMessage()}"
        )
        if record.exc_info:
            base = f"{base}\n{self.formatException(record.exc_info)}"
        return base


def configure_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure root logging with structured formatting and context injection."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ContextFilter())
    if log_format == "text":
        handler.setFormatter(StructuredTextFormatter())
    else:
        handler.setFormatter(StructuredJsonFormatter())

    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    for noisy_logger in ("uvicorn.access",):
        logging.getLogger(noisy_logger).propagate = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)

