"""Unit tests for Phase 2 schemas, DAG validation, and LLM provider factory."""

import pytest
from pydantic import ValidationError

from backend.agents.base.agent import extract_json_payload
from backend.agents.base.llm import MockLLMProvider, create_llm_provider, estimate_cost_usd
from backend.config.settings import Settings
from backend.schemas.task import SubTask
from backend.schemas.workflow import ExecutionPlan, WriterInput


def test_execution_plan_valid_dag_collects_capabilities() -> None:
    """Verify valid DAG passes and aggregates unique required capabilities."""
    plan = ExecutionPlan(
        goal="Build research summary",
        summary="Two-step pipeline",
        subtasks=[
            SubTask(
                task_id="t1",
                title="Research",
                description="Collect docs",
                required_capabilities=["web_search", "summarization"],
            ),
            SubTask(
                task_id="t2",
                title="Analyze",
                description="Analyze docs",
                required_capabilities=["data_analysis", "summarization"],
                depends_on=["t1"],
            ),
        ],
    )
    assert plan.required_capabilities == [
        "web_search",
        "summarization",
        "data_analysis",
    ]


def test_execution_plan_rejects_duplicate_task_ids() -> None:
    """Verify duplicate subtask IDs fail validation."""
    with pytest.raises(ValidationError, match="unique task_id"):
        ExecutionPlan(
            goal="Goal",
            summary="Summary",
            subtasks=[
                SubTask(
                    task_id="dup",
                    title="One",
                    description="First",
                    required_capabilities=["web_search"],
                ),
                SubTask(
                    task_id="dup",
                    title="Two",
                    description="Second",
                    required_capabilities=["data_analysis"],
                ),
            ],
        )


def test_execution_plan_rejects_unknown_dependency() -> None:
    """Verify references to nonexistent dependencies fail validation."""
    with pytest.raises(ValidationError, match="unknown dependency"):
        ExecutionPlan(
            goal="Goal",
            summary="Summary",
            subtasks=[
                SubTask(
                    task_id="t1",
                    title="Task 1",
                    description="Desc",
                    required_capabilities=["web_search"],
                    depends_on=["missing-task"],
                )
            ],
        )


def test_execution_plan_rejects_cycles() -> None:
    """Verify cyclic task dependencies are rejected."""
    with pytest.raises(ValidationError, match="cyclic"):
        ExecutionPlan(
            goal="Goal",
            summary="Summary",
            subtasks=[
                SubTask(
                    task_id="a",
                    title="A",
                    description="Task A",
                    required_capabilities=["web_search"],
                    depends_on=["b"],
                ),
                SubTask(
                    task_id="b",
                    title="B",
                    description="Task B",
                    required_capabilities=["data_analysis"],
                    depends_on=["a"],
                ),
            ],
        )


def test_writer_input_requires_research_or_analysis() -> None:
    """Verify WriterInput fails when neither research nor analysis is given."""
    with pytest.raises(ValidationError, match="requires at least"):
        WriterInput(goal="Write report")


def test_extract_json_payload_handles_code_fences() -> None:
    """Verify markdown fenced JSON blocks are cleanly parsed."""
    raw = '```json\n{"status": "ok", "count": 2}\n```'
    assert extract_json_payload(raw) == {"status": "ok", "count": 2}


def test_extract_json_payload_rejects_non_object() -> None:
    """Verify non-object JSON raises ValueError."""
    with pytest.raises(ValueError, match="JSON object"):
        extract_json_payload("[1, 2, 3]")


def test_create_llm_provider_factory_and_secret_masking() -> None:
    """Verify factory returns MockLLMProvider and requires API keys for real providers."""
    mock_settings = Settings(llm_provider="mock")
    provider = create_llm_provider(mock_settings)
    assert isinstance(provider, MockLLMProvider)

    openai_missing = Settings(llm_provider="openai", openai_api_key=None)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        create_llm_provider(openai_missing)

    secret_settings = Settings(openai_api_key="sk-super-secret-value")
    assert "sk-super-secret-value" not in repr(secret_settings)
    assert estimate_cost_usd("gpt-4o-mini", 1000, 500) > 0

