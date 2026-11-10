"""Unit tests for Phase 2 specialized agents."""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from backend.agents.analyst import AnalystAgent
from backend.agents.base import AgentExecutionError, MockLLMProvider
from backend.agents.planner import PlannerAgent
from backend.agents.researcher import ResearchAgent
from backend.agents.writer import WriterAgent
from backend.schemas.agent import AgentContext
from backend.schemas.workflow import (
    AnalystInput,
    PlannerInput,
    ResearchFinding,
    ResearchInput,
    SourceReference,
    WriterInput,
)


async def test_planner_agent_generates_valid_plan() -> None:
    """Verify PlannerAgent produces a valid DAG plan and execution metrics."""
    agent = PlannerAgent(llm_provider=MockLLMProvider())
    ctx = AgentContext(correlation_id="corr-p2", workflow_id="wf-p2")

    output = await agent.execute(
        PlannerInput(request="Compare FastAPI and Litestar for async microservices."),
        context=ctx,
    )

    assert len(output.plan.subtasks) == 3
    assert output.metrics.provider == "mock"
    assert output.metrics.total_tokens > 0
    assert output.metrics.latency_ms >= 0.0


async def test_research_agent_merges_documents_and_tool_results() -> None:
    """Verify ResearchAgent invokes optional ToolInvoker and preserves input sources."""
    tool_invoker = AsyncMock()
    tool_invoker.invoke = AsyncMock(
        return_value={"results": [{"title": "A2A Spec", "snippet": "Agent cards"}]}
    )
    agent = ResearchAgent(llm_provider=MockLLMProvider(), tool_invoker=tool_invoker)
    doc = SourceReference(
        title="AgentMesh Architecture",
        url="https://example.local/arch",
        snippet="Protocol-driven multi-agent platform",
        source_type="doc",
    )

    output = await agent.execute(
        ResearchInput(query="How does A2A work?", documents=[doc])
    )

    tool_invoker.invoke.assert_awaited_once()
    assert len(output.findings) >= 1
    assert any(src.title == "AgentMesh Architecture" for src in output.sources)


async def test_research_agent_handles_tool_failure_gracefully() -> None:
    """Verify ResearchAgent records tool failures as gaps instead of crashing."""
    failing_tool = AsyncMock()
    failing_tool.invoke = AsyncMock(side_effect=ConnectionError("MCP down"))
    agent = ResearchAgent(llm_provider=MockLLMProvider(), tool_invoker=failing_tool)

    output = await agent.execute(ResearchInput(query="Test query"))

    assert len(output.findings) >= 1
    assert any("ConnectionError" in gap for gap in output.gaps)


async def test_analyst_and_writer_pipeline_preserves_citations() -> None:
    """Verify AnalystAgent and WriterAgent process research into formatted output."""
    provider = MockLLMProvider()
    analyst = AnalystAgent(llm_provider=provider)
    writer = WriterAgent(llm_provider=provider)

    src = SourceReference(
        title="MCP Specification",
        url="https://modelcontextprotocol.io",
        snippet="Standardized tool access",
    )
    finding = ResearchFinding(
        topic="Protocol Separation",
        summary="A2A handles inter-agent delegation; MCP handles tool access.",
        key_facts=["Decouples agent messaging from tool transport"],
        sources=[src],
    )

    analysis = await analyst.execute(
        AnalystInput(
            topic="Protocol Separation",
            research_findings=[finding],
            claims_to_validate=["MCP and A2A serve distinct boundaries"],
        )
    )
    assert len(analysis.insights) >= 1

    from backend.schemas.workflow import ResearchOutput

    research = ResearchOutput(
        query="Protocol Separation",
        findings=[finding],
        sources=[src],
    )
    report = await writer.execute(
        WriterInput(
            goal="Explain AgentMesh protocols",
            research=research,
            analysis=analysis,
            output_format="json",
        )
    )
    assert report.output_format == "json"
    assert '"title"' in report.formatted_content
    assert any(c.title == "MCP Specification" for c in report.citations)


async def test_agent_rejects_invalid_input_and_malformed_llm_output() -> None:
    """Verify BaseAgent raises AgentExecutionError on invalid input or bad JSON."""
    agent = PlannerAgent(llm_provider=MockLLMProvider())
    with pytest.raises(AgentExecutionError, match="Invalid input payload"):
        await agent.execute({"request": ""})

    broken_provider = MockLLMProvider(responder=lambda _req: "not-valid-json")
    broken_agent = PlannerAgent(llm_provider=broken_provider)
    with pytest.raises(AgentExecutionError, match="Failed to parse structured LLM output"):
        await broken_agent.execute(PlannerInput(request="Valid request"))

