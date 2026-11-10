"""Analyst Agent: evaluates findings, spots patterns, and validates claims."""

import json

from pydantic import BaseModel, Field

from backend.agents.base.agent import BaseAgent
from backend.agents.base.llm import LLMProvider
from backend.schemas.agent import AgentContext, AgentIdentity
from backend.schemas.workflow import (
    AnalystInput,
    AnalystOutput,
    ClaimValidation,
    ComparisonItem,
)

_ANALYST_SYSTEM_PROMPT = (
    "You are the AgentMesh Analyst Agent. Analyze research findings, compare "
    "options, detect patterns, generate insights, and validate claims against "
    "available evidence. Output a single JSON object with keys: topic (string), "
    "patterns (list of strings), insights (list of strings), comparisons "
    "(list of {dimension, observations, takeaway}), claim_validations (list of "
    "{claim, verdict, evidence}), confidence_score (float 0..1)."
)


class _AnalystPayload(BaseModel):
    topic: str = Field(..., min_length=1)
    patterns: list[str] = Field(default_factory=list)
    insights: list[str] = Field(..., min_length=1)
    comparisons: list[ComparisonItem] = Field(default_factory=list)
    claim_validations: list[ClaimValidation] = Field(default_factory=list)
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)


def default_analyst_identity() -> AgentIdentity:
    """Return the default AgentIdentity for the Analyst Agent."""
    return AgentIdentity(
        agent_id="analyst-agent-001",
        name="Analyst Agent",
        description="Analyzes research results, detects patterns, and validates claims.",
        capabilities=[
            "data_analysis",
            "comparative_analysis",
            "pattern_recognition",
            "insight_generation",
            "claim_validation",
        ],
        protocol="A2A",
    )


class AnalystAgent(BaseAgent[AnalystInput, AnalystOutput]):
    """Specialized agent responsible for synthesis and evidence validation."""

    input_schema = AnalystInput
    output_schema = AnalystOutput
    agent_role = "analyst"

    def __init__(
        self,
        llm_provider: LLMProvider,
        identity: AgentIdentity | None = None,
    ) -> None:
        super().__init__(
            identity=identity or default_analyst_identity(),
            llm_provider=llm_provider,
        )

    async def _run(
        self, payload: AnalystInput, context: AgentContext
    ) -> AnalystOutput:
        prompt_data = {
            "topic": payload.topic,
            "research_findings": [f.model_dump() for f in payload.research_findings],
            "claims_to_validate": payload.claims_to_validate,
            "evaluation_criteria": payload.evaluation_criteria,
        }
        user_prompt = (
            "Analyze the research findings and validate any listed claims:\n"
            f"{json.dumps(prompt_data, indent=2)}"
        )
        parsed, metrics = await self._generate_structured(
            system_prompt=_ANALYST_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=_AnalystPayload,
        )
        return AnalystOutput(
            topic=parsed.topic,
            patterns=parsed.patterns,
            insights=parsed.insights,
            comparisons=parsed.comparisons,
            claim_validations=parsed.claim_validations,
            confidence_score=parsed.confidence_score,
            metrics=metrics,
        )

