"""Planner Agent: decomposes requests into DAG execution plans."""

import json

from backend.agents.base.agent import BaseAgent
from backend.agents.base.llm import LLMProvider
from backend.schemas.agent import AgentContext, AgentIdentity
from backend.schemas.workflow import ExecutionPlan, PlannerInput, PlannerOutput

_PLANNER_SYSTEM_PROMPT = (
    "You are the AgentMesh Planner Agent. Decompose the user request into a "
    "directed acyclic graph (DAG) of subtasks. Output a single JSON object with "
    "keys: goal (string), summary (string), subtasks (list of objects with "
    "task_id, title, description, required_capabilities, depends_on, priority)."
)


def default_planner_identity() -> AgentIdentity:
    """Return the default AgentIdentity for the Planner Agent."""
    return AgentIdentity(
        agent_id="planner-agent-001",
        name="Planner Agent",
        description="Decomposes complex user requests into capability-tagged DAG plans.",
        capabilities=[
            "task_decomposition",
            "execution_planning",
            "capability_identification",
            "dependency_mapping",
        ],
        protocol="A2A",
    )


class PlannerAgent(BaseAgent[PlannerInput, PlannerOutput]):
    """Specialized agent responsible for task decomposition and planning."""

    input_schema = PlannerInput
    output_schema = PlannerOutput
    agent_role = "planner"

    def __init__(
        self,
        llm_provider: LLMProvider,
        identity: AgentIdentity | None = None,
    ) -> None:
        super().__init__(
            identity=identity or default_planner_identity(),
            llm_provider=llm_provider,
        )

    async def _run(self, payload: PlannerInput, context: AgentContext) -> PlannerOutput:
        prompt_context = {
            "request": payload.request,
            "constraints": payload.constraints,
            "available_capabilities": payload.available_capabilities,
            "context": payload.context,
        }
        user_prompt = (
            f"Create an execution plan for the following request:\n"
            f"{json.dumps(prompt_context, indent=2)}"
        )
        plan, metrics = await self._generate_structured(
            system_prompt=_PLANNER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=ExecutionPlan,
        )
        return PlannerOutput(plan=plan, metrics=metrics)

