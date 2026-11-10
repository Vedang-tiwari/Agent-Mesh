"""Writer Agent: synthesizes research and analysis into formatted reports."""

import json

from pydantic import BaseModel, Field

from backend.agents.base.agent import BaseAgent
from backend.agents.base.llm import LLMProvider
from backend.schemas.agent import AgentContext, AgentIdentity
from backend.schemas.workflow import (
    ReportSection,
    SourceReference,
    WriterInput,
    WriterOutput,
)

_WRITER_SYSTEM_PROMPT = (
    "You are the AgentMesh Writer Agent. Combine research findings and analytical "
    "insights into a clear, well-structured report with citations when sources are "
    "available. Output a single JSON object with keys: title (string), "
    "executive_summary (string), sections (list of {heading, content}), "
    "formatted_content (string), citations (list of {title, url, snippet, source_type})."
)


class _WriterPayload(BaseModel):
    title: str = Field(..., min_length=1)
    executive_summary: str = Field(..., min_length=1)
    sections: list[ReportSection] = Field(..., min_length=1)
    formatted_content: str = Field(..., min_length=1)
    citations: list[SourceReference] = Field(default_factory=list)


def default_writer_identity() -> AgentIdentity:
    """Return the default AgentIdentity for the Writer Agent."""
    return AgentIdentity(
        agent_id="writer-agent-001",
        name="Writer Agent",
        description="Generates structured reports and formatted deliverables with citations.",
        capabilities=[
            "report_writing",
            "content_synthesis",
            "output_formatting",
            "citation_formatting",
        ],
        protocol="A2A",
    )


class WriterAgent(BaseAgent[WriterInput, WriterOutput]):
    """Specialized agent responsible for final report synthesis and formatting."""

    input_schema = WriterInput
    output_schema = WriterOutput
    agent_role = "writer"

    def __init__(
        self,
        llm_provider: LLMProvider,
        identity: AgentIdentity | None = None,
    ) -> None:
        super().__init__(
            identity=identity or default_writer_identity(),
            llm_provider=llm_provider,
        )

    async def _run(self, payload: WriterInput, context: AgentContext) -> WriterOutput:
        prompt_data = {
            "goal": payload.goal,
            "output_format": payload.output_format,
            "audience": payload.audience,
            "research": payload.research.model_dump() if payload.research else None,
            "analysis": payload.analysis.model_dump() if payload.analysis else None,
        }
        user_prompt = (
            "Generate a structured final report from the provided inputs:\n"
            f"{json.dumps(prompt_data, indent=2)}"
        )
        parsed, metrics = await self._generate_structured(
            system_prompt=_WRITER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=_WriterPayload,
        )

        citations = list(parsed.citations)
        if payload.research is not None:
            seen = {(c.title, c.url) for c in citations}
            for src in payload.research.sources:
                key = (src.title, src.url)
                if key not in seen:
                    seen.add(key)
                    citations.append(src)

        formatted_content = parsed.formatted_content
        if payload.output_format == "json":
            formatted_content = json.dumps(
                {
                    "title": parsed.title,
                    "executive_summary": parsed.executive_summary,
                    "sections": [s.model_dump() for s in parsed.sections],
                    "citations": [c.model_dump() for c in citations],
                },
                indent=2,
            )

        return WriterOutput(
            title=parsed.title,
            executive_summary=parsed.executive_summary,
            sections=parsed.sections,
            formatted_content=formatted_content,
            citations=citations,
            output_format=payload.output_format,
            metrics=metrics,
        )

