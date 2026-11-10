"""Base agent interface, execution lifecycle, and structured LLM helpers."""

from abc import ABC, abstractmethod
import json
import re
import time
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, ValidationError

from backend.agents.base.llm import LLMMessage, LLMProvider, LLMRequest, LLMResponse
from backend.infrastructure.logging import (
    get_logger,
    reset_correlation_id,
    reset_workflow_id,
    set_correlation_id,
    set_workflow_id,
)
from backend.infrastructure.telemetry import get_tracer
from backend.schemas.agent import (
    AgentContext,
    AgentExecutionMetrics,
    AgentIdentity,
)

logger = get_logger(__name__)
tracer = get_tracer(__name__)

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)
SchemaT = TypeVar("SchemaT", bound=BaseModel)

_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```$", re.DOTALL | re.IGNORECASE)


class AgentExecutionError(RuntimeError):
    """Raised when agent input validation, execution, or output parsing fails."""

    def __init__(self, agent_id: str, message: str) -> None:
        self.agent_id = agent_id
        super().__init__(f"[{agent_id}] {message}")


@runtime_checkable
class ToolInvoker(Protocol):
    """Protocol for invoking external tools (implemented by MCP in Phase 3)."""

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke a named tool with structured arguments and return JSON-like output."""
        ...


def extract_json_payload(raw_text: str) -> dict[str, Any]:
    """Parse JSON from raw LLM text, stripping optional markdown code fences."""
    cleaned = raw_text.strip()
    match = _FENCE_RE.match(cleaned)
    if match:
        cleaned = match.group(1).strip()
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object at top level of LLM output")
    return parsed


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """Abstract base class for all specialized AgentMesh agents."""

    input_schema: type[InputT]
    output_schema: type[OutputT]
    agent_role: str = "agent"

    def __init__(
        self,
        identity: AgentIdentity,
        llm_provider: LLMProvider,
        tool_invoker: ToolInvoker | None = None,
    ) -> None:
        self.identity = identity
        self.llm_provider = llm_provider
        self.tool_invoker = tool_invoker

    @property
    def agent_id(self) -> str:
        """Return the agent's unique identifier."""
        return self.identity.agent_id

    async def execute(
        self,
        raw_input: InputT | dict[str, Any],
        context: AgentContext | None = None,
    ) -> OutputT:
        """Validate input, propagate trace/log context, execute, and validate output."""
        active_context = context or AgentContext()
        corr_token = set_correlation_id(active_context.correlation_id)
        wf_token = set_workflow_id(active_context.workflow_id)
        start = time.perf_counter()

        try:
            try:
                validated_input = (
                    raw_input
                    if isinstance(raw_input, self.input_schema)
                    else self.input_schema.model_validate(raw_input)
                )
            except ValidationError as exc:
                raise AgentExecutionError(
                    self.agent_id, f"Invalid input payload: {exc}"
                ) from exc

            logger.info(
                "Starting agent execution",
                extra={"agent_id": self.agent_id, "task_id": active_context.task_id},
            )

            with tracer.start_as_current_span(f"agent.execute.{self.agent_id}"):
                result = await self._run(validated_input, active_context)

            if not isinstance(result, self.output_schema):
                result = self.output_schema.model_validate(result)

            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            if hasattr(result, "metrics") and isinstance(
                result.metrics, AgentExecutionMetrics
            ):
                result.metrics.latency_ms = elapsed_ms

            logger.info(
                "Completed agent execution",
                extra={
                    "agent_id": self.agent_id,
                    "task_id": active_context.task_id,
                    "latency_ms": elapsed_ms,
                },
            )
            return result
        except AgentExecutionError:
            raise
        except Exception as exc:
            logger.exception(
                "Agent execution failed",
                extra={
                    "agent_id": self.agent_id,
                    "task_id": active_context.task_id,
                    "error_type": type(exc).__name__,
                },
            )
            raise AgentExecutionError(
                self.agent_id, f"Execution failed: {exc}"
            ) from exc
        finally:
            reset_workflow_id(wf_token)
            reset_correlation_id(corr_token)

    @abstractmethod
    async def _run(self, payload: InputT, context: AgentContext) -> OutputT:
        """Execute domain logic for the validated agent input."""

    async def _generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[SchemaT],
    ) -> tuple[SchemaT, AgentExecutionMetrics]:
        """Call the configured LLMProvider and validate JSON output against a schema."""
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt),
            ],
            json_mode=True,
            metadata={"agent_role": self.agent_role, "agent_id": self.agent_id},
        )
        llm_response: LLMResponse = await self.llm_provider.generate(request)

        try:
            raw_obj = extract_json_payload(llm_response.content)
            parsed = schema.model_validate(raw_obj)
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            raise AgentExecutionError(
                self.agent_id, f"Failed to parse structured LLM output: {exc}"
            ) from exc

        metrics = AgentExecutionMetrics(
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            total_tokens=llm_response.total_tokens,
            estimated_cost_usd=llm_response.estimated_cost_usd,
            latency_ms=llm_response.latency_ms,
            model=llm_response.model,
            provider=llm_response.provider,
        )
        return parsed, metrics

