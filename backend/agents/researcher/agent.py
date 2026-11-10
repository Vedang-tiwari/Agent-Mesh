"""Research Agent: gathers information, reads documents, and structures findings."""

import json
from typing import Any

from pydantic import BaseModel, Field

from backend.agents.base.agent import BaseAgent, ToolInvoker
from backend.agents.base.llm import LLMProvider
from backend.infrastructure.logging import get_logger
from backend.schemas.agent import AgentContext, AgentIdentity
from backend.schemas.workflow import (
    ResearchFinding,
    ResearchInput,
    ResearchOutput,
    SourceReference,
)

logger = get_logger(__name__)

_RESEARCH_SYSTEM_PROMPT = (
    "You are the AgentMesh Research Agent. Synthesize evidence from the provided "
    "documents and tool results into structured research findings. Output a single "
    "JSON object with keys: query (string), findings (list of {topic, summary, "
    "key_facts, sources, confidence}), sources (list of {title, url, snippet, "
    "source_type}), gaps (list of strings)."
)


class _ResearchPayload(BaseModel):
    query: str = Field(..., min_length=1)
    findings: list[ResearchFinding] = Field(..., min_length=1)
    sources: list[SourceReference] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


def default_researcher_identity() -> AgentIdentity:
    """Return the default AgentIdentity for the Research Agent."""
    return AgentIdentity(
        agent_id="research-agent-001",
        name="Research Agent",
        description="Performs web search, document retrieval, and structured extraction.",
        capabilities=[
            "web_search",
            "document_retrieval",
            "document_reading",
            "information_extraction",
            "summarization",
        ],
        protocol="A2A",
    )


class ResearchAgent(BaseAgent[ResearchInput, ResearchOutput]):
    """Specialized agent responsible for information gathering and extraction."""

    input_schema = ResearchInput
    output_schema = ResearchOutput
    agent_role = "researcher"

    def __init__(
        self,
        llm_provider: LLMProvider,
        identity: AgentIdentity | None = None,
        tool_invoker: ToolInvoker | None = None,
    ) -> None:
        super().__init__(
            identity=identity or default_researcher_identity(),
            llm_provider=llm_provider,
            tool_invoker=tool_invoker,
        )

    async def _run(
        self, payload: ResearchInput, context: AgentContext
    ) -> ResearchOutput:
        tool_results: list[dict[str, Any]] = []
        tool_gaps: list[str] = []

        if self.tool_invoker is not None:
            try:
                raw_tool = await self.tool_invoker.invoke(
                    "search",
                    {"query": payload.query, "max_results": payload.max_results},
                )
                tool_results.append(raw_tool)
            except Exception as exc:
                logger.warning(
                    "Research tool invocation failed; continuing with available context",
                    extra={"error_type": type(exc).__name__},
                )
                tool_gaps.append(f"External search tool unavailable: {type(exc).__name__}")

        prompt_data = {
            "query": payload.query,
            "focus_areas": payload.focus_areas,
            "documents": [doc.model_dump() for doc in payload.documents],
            "tool_results": tool_results,
        }
        user_prompt = (
            "Synthesize structured research findings from this material:\n"
            f"{json.dumps(prompt_data, indent=2)}"
        )

        parsed, metrics = await self._generate_structured(
            system_prompt=_RESEARCH_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=_ResearchPayload,
        )

        merged_sources = list(parsed.sources)
        seen_keys = {(s.title, s.url) for s in merged_sources}
        for doc in payload.documents:
            key = (doc.title, doc.url)
            if key not in seen_keys:
                seen_keys.add(key)
                merged_sources.append(doc)

        return ResearchOutput(
            query=parsed.query,
            findings=parsed.findings,
            sources=merged_sources,
            gaps=[*parsed.gaps, *tool_gaps],
            metrics=metrics,
        )

