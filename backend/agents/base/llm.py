"""LLM provider abstraction and implementations for AgentMesh agents."""

from collections.abc import Callable
import json
import time
from typing import Any, Literal, Protocol, runtime_checkable

import httpx
from pydantic import BaseModel, Field

from backend.config.settings import Settings
from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Approximate per-1M-token USD pricing for cost estimation when provider omits cost.
_MODEL_PRICING_PER_1M: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "claude-3-5-haiku-latest": (0.80, 4.00),
    "claude-3-5-sonnet-latest": (3.00, 15.00),
}


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider invocation fails."""


class LLMMessage(BaseModel):
    """Single message in an LLM chat completion request."""

    role: Literal["system", "user", "assistant"]
    content: str = Field(..., min_length=1)


class LLMRequest(BaseModel):
    """Provider-agnostic LLM generation request."""

    messages: list[LLMMessage] = Field(..., min_length=1)
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=32768)
    json_mode: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Provider-agnostic LLM generation response with usage metrics."""

    content: str
    model: str
    provider: str
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)
    latency_ms: float = Field(default=0.0, ge=0.0)


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol implemented by all LLM provider adapters."""

    provider_name: str

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Execute a completion request and return a structured LLMResponse."""
        ...


def estimate_cost_usd(
    model: str, prompt_tokens: int, completion_tokens: int
) -> float:
    """Estimate USD cost for token usage based on known reference rates."""
    input_rate, output_rate = _MODEL_PRICING_PER_1M.get(model, (0.50, 1.50))
    cost = (prompt_tokens * input_rate + completion_tokens * output_rate) / 1_000_000
    return round(cost, 8)


class MockLLMProvider:
    """Deterministic LLM provider for testing and offline development."""

    provider_name = "mock"

    def __init__(
        self,
        model: str = "mock-agentmesh-v1",
        responder: Callable[[LLMRequest], str] | None = None,
    ) -> None:
        self.model = model
        self._responder = responder

    async def generate(self, request: LLMRequest) -> LLMResponse:
        start = time.perf_counter()
        active_model = request.model or self.model
        prompt_text = "\n".join(msg.content for msg in request.messages)
        prompt_tokens = max(1, len(prompt_text.split()))

        if self._responder is not None:
            content = self._responder(request)
        else:
            content = self._default_structured_response(request)

        completion_tokens = max(1, len(content.split()))
        latency_ms = round((time.perf_counter() - start) * 1000, 3)

        return LLMResponse(
            content=content,
            model=active_model,
            provider=self.provider_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=estimate_cost_usd(
                active_model, prompt_tokens, completion_tokens
            ),
            latency_ms=latency_ms,
        )

    def _default_structured_response(self, request: LLMRequest) -> str:
        role_hint = str(request.metadata.get("agent_role", "")).lower()
        user_prompt = request.messages[-1].content

        if role_hint == "planner":
            payload: dict[str, Any] = {
                "goal": user_prompt[:200],
                "summary": "Decomposed request into research, analysis, and synthesis.",
                "subtasks": [
                    {
                        "task_id": "task-research-1",
                        "title": "Gather background research",
                        "description": f"Research primary facts for: {user_prompt[:120]}",
                        "required_capabilities": ["web_search", "summarization"],
                        "depends_on": [],
                        "priority": 1,
                    },
                    {
                        "task_id": "task-analysis-1",
                        "title": "Analyze collected findings",
                        "description": "Compare findings, detect patterns, and validate claims.",
                        "required_capabilities": ["data_analysis", "claim_validation"],
                        "depends_on": ["task-research-1"],
                        "priority": 2,
                    },
                    {
                        "task_id": "task-write-1",
                        "title": "Produce final report",
                        "description": "Synthesize research and analysis with citations.",
                        "required_capabilities": ["report_writing"],
                        "depends_on": ["task-analysis-1"],
                        "priority": 3,
                    },
                ],
            }
            return json.dumps(payload)

        if role_hint == "researcher":
            payload = {
                "query": user_prompt[:200],
                "findings": [
                    {
                        "topic": "Primary Research Synthesis",
                        "summary": f"Structured findings gathered for query: {user_prompt[:120]}",
                        "key_facts": [
                            "Identified core requirements and reference architecture.",
                            "Collected supporting context from provided inputs.",
                        ],
                        "sources": [],
                        "confidence": 0.85,
                    }
                ],
                "sources": [],
                "gaps": ["Live external search tools are connected in Phase 3 (MCP)."],
            }
            return json.dumps(payload)

        if role_hint == "analyst":
            payload = {
                "topic": user_prompt[:200],
                "patterns": ["Consistent alignment across collected evidence"],
                "insights": [
                    "Primary evidence supports a modular, phased implementation strategy."
                ],
                "comparisons": [],
                "claim_validations": [],
                "confidence_score": 0.85,
            }
            return json.dumps(payload)

        if role_hint == "writer":
            payload = {
                "title": "AgentMesh Synthesis Report",
                "executive_summary": (
                    "Consolidated findings and analytical insights generated by AgentMesh."
                ),
                "sections": [
                    {
                        "heading": "Overview",
                        "content": f"Report prepared for goal: {user_prompt[:150]}",
                    },
                    {
                        "heading": "Key Insights",
                        "content": "Evidence reviewed and synthesized into actionable conclusions.",
                    },
                ],
                "formatted_content": (
                    "# AgentMesh Synthesis Report\n\n"
                    "## Overview\n"
                    f"Report prepared for goal: {user_prompt[:150]}\n\n"
                    "## Key Insights\n"
                    "Evidence reviewed and synthesized into actionable conclusions.\n"
                ),
                "citations": [],
            }
            return json.dumps(payload)

        return json.dumps({"response": "ok"})


class OpenAICompatibleLLMProvider:
    """Adapter for OpenAI and OpenAI-compatible Chat Completions APIs."""

    provider_name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
        default_temperature: float = 0.2,
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be configured for OpenAI provider")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._default_temperature = default_temperature

    async def generate(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self._model
        temperature = (
            request.temperature
            if request.temperature is not None
            else self._default_temperature
        )
        body: dict[str, Any] = {
            "model": model,
            "messages": [msg.model_dump() for msg in request.messages],
            "temperature": temperature,
            "max_tokens": request.max_tokens,
        }
        if request.json_mode:
            body["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=body,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"OpenAI request failed ({type(exc).__name__})"
            ) from exc

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        choices = data.get("choices") or []
        if not choices:
            raise LLMProviderError("OpenAI response contained no choices")

        content = choices[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))

        return LLMResponse(
            content=content,
            model=model,
            provider=self.provider_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimate_cost_usd(
                model, prompt_tokens, completion_tokens
            ),
            latency_ms=latency_ms,
        )


class AnthropicLLMProvider:
    """Adapter for the Anthropic Messages API."""

    provider_name = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-latest",
        base_url: str = "https://api.anthropic.com/v1",
        timeout: float = 30.0,
        default_temperature: float = 0.2,
    ) -> None:
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY must be configured for Anthropic provider"
            )
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._default_temperature = default_temperature

    async def generate(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self._model
        temperature = (
            request.temperature
            if request.temperature is not None
            else self._default_temperature
        )
        system_parts = [m.content for m in request.messages if m.role == "system"]
        chat_messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if m.role != "system"
        ]
        body: dict[str, Any] = {
            "model": model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": request.max_tokens,
        }
        if system_parts:
            body["system"] = "\n\n".join(system_parts)

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/messages",
                    headers=headers,
                    json=body,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"Anthropic request failed ({type(exc).__name__})"
            ) from exc

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        blocks = data.get("content") or []
        content = "".join(
            block.get("text", "") for block in blocks if block.get("type") == "text"
        )
        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("input_tokens", 0))
        completion_tokens = int(usage.get("output_tokens", 0))

        return LLMResponse(
            content=content,
            model=model,
            provider=self.provider_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=estimate_cost_usd(
                model, prompt_tokens, completion_tokens
            ),
            latency_ms=latency_ms,
        )


def create_llm_provider(settings: Settings) -> LLMProvider:
    """Instantiate the configured LLMProvider from application settings."""
    if settings.llm_provider == "mock":
        return MockLLMProvider(model=settings.llm_model)

    if settings.llm_provider == "openai":
        api_key = (
            settings.openai_api_key.get_secret_value()
            if settings.openai_api_key
            else ""
        )
        return OpenAICompatibleLLMProvider(
            api_key=api_key,
            model=settings.llm_model,
            base_url=settings.openai_base_url,
            timeout=settings.llm_timeout,
            default_temperature=settings.llm_temperature,
        )

    if settings.llm_provider == "anthropic":
        api_key = (
            settings.anthropic_api_key.get_secret_value()
            if settings.anthropic_api_key
            else ""
        )
        return AnthropicLLMProvider(
            api_key=api_key,
            model=settings.llm_model,
            base_url=settings.anthropic_base_url,
            timeout=settings.llm_timeout,
            default_temperature=settings.llm_temperature,
        )

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")

