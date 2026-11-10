"""Task decomposition and execution result schemas."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from backend.schemas.agent import AgentExecutionMetrics


class TaskStatus(StrEnum):
    """Execution state of an individual workflow subtask."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SubTask(BaseModel):
    """A decomposed unit of work produced by the Planner Agent."""

    task_id: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=256)
    description: str = Field(..., min_length=1, max_length=4096)
    required_capabilities: list[str] = Field(default_factory=list, min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    assigned_agent_id: str | None = None
    priority: int = Field(default=1, ge=1, le=10)
    input_data: dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    """Standardized output produced after executing a subtask."""

    task_id: str = Field(..., min_length=1)
    agent_id: str = Field(..., min_length=1)
    status: TaskStatus
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    metrics: AgentExecutionMetrics = Field(default_factory=AgentExecutionMetrics)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

