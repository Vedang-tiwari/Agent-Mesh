"""Agent identity, execution context, and telemetry metric schemas."""

from enum import StrEnum
from typing import Any
import uuid

from pydantic import BaseModel, Field


class AgentStatus(StrEnum):
    """Operational lifecycle state of a registered agent."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class AgentIdentity(BaseModel):
    """Structured metadata describing an AgentMesh agent."""

    agent_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(..., min_length=1, max_length=1024)
    capabilities: list[str] = Field(default_factory=list, min_length=1)
    protocol: str = Field(default="A2A", min_length=1, max_length=32)
    endpoint: str | None = Field(default=None, max_length=512)
    status: AgentStatus = AgentStatus.ACTIVE
    version: str = Field(default="0.1.0", min_length=1, max_length=32)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentExecutionMetrics(BaseModel):
    """Resource consumption and latency metrics for an agent execution."""

    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)
    latency_ms: float = Field(default=0.0, ge=0.0)
    model: str | None = None
    provider: str | None = None


class AgentContext(BaseModel):
    """Execution context propagated across agent invocations."""

    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str | None = None
    task_id: str | None = None
    caller_agent_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

