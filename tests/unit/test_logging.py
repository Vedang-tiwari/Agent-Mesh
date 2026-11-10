"""Unit tests for structured logging and context propagation."""

import json
import logging

from backend.infrastructure.logging import (
    ContextFilter,
    StructuredJsonFormatter,
    StructuredTextFormatter,
    reset_correlation_id,
    reset_workflow_id,
    set_correlation_id,
    set_workflow_id,
)


def _make_record(msg: str, **extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="agentmesh.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_includes_context_and_extra() -> None:
    """Verify JSON logs capture correlation_id, workflow_id, and extra fields."""
    corr_token = set_correlation_id("corr-123")
    wf_token = set_workflow_id("wf-456")
    try:
        record = _make_record("Task dispatched", agent_id="research-001")
        ContextFilter().filter(record)
        rendered = StructuredJsonFormatter().format(record)
        payload = json.loads(rendered)

        assert payload["level"] == "INFO"
        assert payload["logger"] == "agentmesh.test"
        assert payload["message"] == "Task dispatched"
        assert payload["correlation_id"] == "corr-123"
        assert payload["workflow_id"] == "wf-456"
        assert payload["agent_id"] == "research-001"
        assert "timestamp" in payload
    finally:
        reset_workflow_id(wf_token)
        reset_correlation_id(corr_token)


def test_text_formatter_renders_context() -> None:
    """Verify text formatter includes readable correlation and workflow IDs."""
    corr_token = set_correlation_id("corr-abc")
    try:
        record = _make_record("Ready")
        ContextFilter().filter(record)
        rendered = StructuredTextFormatter().format(record)
        assert "INFO" in rendered
        assert "corr=corr-abc" in rendered
        assert "wf=-" in rendered
        assert "Ready" in rendered
    finally:
        reset_correlation_id(corr_token)

