# AgentMesh — Coding Agent Instructions

## 1. Project Overview

You are working on **AgentMesh**, a Python-based distributed multi-agent orchestration platform.

The objective is to build a reusable, modular, extensible platform that allows independently developed AI agents to:

- Register themselves with a central agent registry.
- Discover other agents dynamically.
- Communicate through the A2A (Agent2Agent) protocol.
- Access external tools and resources through MCP (Model Context Protocol).
- Delegate tasks to specialized agents.
- Execute multi-agent workflows.
- Share structured information and workflow context.
- Recover from failures and handle execution errors.
- Monitor agent health, performance, and resource consumption.

This must be engineered as a software infrastructure platform, not merely a chatbot with multiple agents.

### Core Philosophy

AgentMesh should provide the infrastructure required to build, connect, coordinate, execute, and monitor distributed AI agents.

The platform should be:

- Modular.
- Protocol-driven.
- Scalable.
- Asynchronous.
- Fault-tolerant.
- Observable.
- Secure.
- Extensible.

---

# 2. Core Architecture

Implement the following architectural components.

### A. Agent Registry

A centralized service responsible for managing registered agents.

Responsibilities:

- Agent registration.
- Agent deregistration.
- Agent discovery.
- Capability-based discovery.
- Agent metadata management.
- Agent endpoint management.
- Agent health monitoring.
- Agent status tracking.

Each agent must have a structured identity.

Example:

```json
{
  "agent_id": "research-agent-001",
  "name": "Research Agent",
  "description": "Performs research and information retrieval",
  "capabilities": [
    "web_search",
    "document_retrieval",
    "summarization"
  ],
  "protocol": "A2A",
  "endpoint": "http://localhost:8001",
  "status": "active"
}
```

Use A2A Agent Cards for protocol-level agent discovery and capability descriptions.

Do not confuse the internal registry with the A2A protocol itself. The registry manages platform-wide metadata; Agent Cards expose standardized agent information.

### B. Orchestration Engine

The orchestration engine coordinates multi-agent workflows.

Responsibilities:

- Receive user requests.
- Understand task requirements.
- Decompose complex tasks into subtasks.
- Identify required agent capabilities.
- Discover suitable agents.
- Assign tasks.
- Execute independent tasks concurrently.
- Manage task dependencies.
- Aggregate agent responses.
- Handle execution failures.
- Produce final outputs.

Use LangGraph for workflow orchestration where appropriate.

Do not tightly couple the orchestration engine to a specific LLM provider.

### C. A2A Communication Layer

Implement standardized agent-to-agent communication.

Responsibilities:

- Agent discovery.
- Agent Card handling.
- Task delegation.
- Task execution requests.
- Task status tracking.
- Structured message exchange.
- Response handling.
- Error propagation.

Use the official A2A Python SDK.

Avoid implementing a custom communication protocol when A2A already provides the required functionality.

### D. MCP Integration Layer

Implement MCP-based tool integration.

Agents must be able to access external capabilities through MCP servers.

Initial MCP servers:

1. Search MCP Server
2. Filesystem MCP Server
3. Database MCP Server
4. GitHub MCP Server

Responsibilities:

- MCP client management.
- MCP server connections.
- Tool discovery.
- Tool invocation.
- Structured tool responses.
- Connection management.
- Error handling.

Use the official MCP Python SDK.

Keep MCP tool execution separate from A2A agent communication.

### E. Memory and State Management

Implement persistent workflow and execution state.

Use:

**Redis**
- Temporary workflow state.
- Task execution status.
- Distributed coordination where necessary.
- Caching.
- Short-lived context.

**PostgreSQL**
- Agent metadata.
- Workflow definitions.
- Execution history.
- Task records.
- Audit logs.
- User and organization data.

**Qdrant (optional initial implementation)**
- Semantic memory.
- Embedding storage.
- Context retrieval.

Do not introduce vector storage unless a concrete semantic retrieval requirement exists.

### F. Observability Layer

Implement platform-wide monitoring.

Track:

- Agent execution time.
- Workflow execution time.
- Task success/failure.
- Agent availability.
- LLM token consumption.
- Estimated LLM costs.
- MCP tool calls.
- A2A communication failures.
- Retry attempts.
- Latency.
- Errors and exceptions.

Use OpenTelemetry-compatible instrumentation.

Provide structured logging with correlation IDs and workflow IDs.

---

# 3. Recommended Technology Stack

Use the following technologies unless there is a strong technical reason to change them.

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Backend | FastAPI |
| Agent Framework | LangGraph |
| Agent Communication | A2A Python SDK |
| Tool Integration | MCP Python SDK |
| MCP Server Development | FastMCP |
| LLM Integration | Provider abstraction |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Cache | Redis |
| Validation | Pydantic |
| Async Processing | asyncio |
| Vector Database | Qdrant (optional) |
| Authentication | JWT |
| Containerization | Docker |
| Monitoring | OpenTelemetry |
| Testing | Pytest |
| Frontend | React / Next.js (later phase) |

Use maintained official SDKs and compatible versions.

Before implementing protocol integrations, inspect the installed SDK documentation and examples. Do not assume APIs from outdated tutorials.

---

# 4. Project Directory Structure

Maintain a clean and modular architecture.

```text
AgentMesh/
│
├── backend/
│   │
│   ├── api/
│   │   ├── routes/
│   │   │   ├── agents.py
│   │   │   ├── workflows.py
│   │   │   ├── executions.py
│   │   │   └── health.py
│   │   ├── dependencies.py
│   │   └── main.py
│   │
│   ├── core/
│   │   ├── orchestrator.py
│   │   ├── task_scheduler.py
│   │   ├── workflow_engine.py
│   │   ├── agent_registry.py
│   │   └── discovery.py
│   │
│   ├── agents/
│   │   ├── base/
│   │   ├── planner/
│   │   ├── researcher/
│   │   ├── analyst/
│   │   └── writer/
│   │
│   ├── protocols/
│   │   ├── a2a/
│   │   │   ├── client.py
│   │   │   ├── server.py
│   │   │   └── models.py
│   │   │
│   │   └── mcp/
│   │       ├── client.py
│   │       ├── manager.py
│   │       └── models.py
│   │
│   ├── memory/
│   │   ├── redis_store.py
│   │   ├── postgres_store.py
│   │   └── context_manager.py
│   │
│   ├── infrastructure/
│   │   ├── database.py
│   │   ├── redis.py
│   │   ├── logging.py
│   │   └── telemetry.py
│   │
│   ├── schemas/
│   │   ├── agent.py
│   │   ├── task.py
│   │   └── workflow.py
│   │
│   ├── services/
│   │   ├── agent_service.py
│   │   ├── workflow_service.py
│   │   └── execution_service.py
│   │
│   ├── config/
│   │   └── settings.py
│   │
│   └── main.py
│
├── mcp_servers/
│   ├── search_server.py
│   ├── filesystem_server.py
│   ├── database_server.py
│   └── github_server.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── scripts/
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── development.md
│
├── frontend/
│
├── docker/
│
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pyproject.toml
├── alembic.ini
├── README.md
└── INSTRUCTION.md
```

You may adjust the structure when implementation requirements justify it, but preserve separation of responsibilities.

---

# 5. Initial Agent Implementations

Create the following specialized agents.

### 1. Planner Agent

Responsibilities:
- Understand user requests.
- Decompose complex tasks.
- Generate execution plans.
- Identify required capabilities.
- Define task dependencies.

### 2. Research Agent

Responsibilities:
- Search the web.
- Retrieve documentation.
- Read documents.
- Extract relevant information.
- Return structured research findings.

### 3. Analyst Agent

Responsibilities:
- Analyze research results.
- Compare information.
- Identify patterns.
- Generate insights.
- Validate claims against available evidence.

### 4. Writer Agent

Responsibilities:
- Combine results.
- Generate structured reports.
- Format outputs.
- Include relevant citations when sources are available.

Agents must have clearly defined input and output schemas.

Avoid creating agents that duplicate responsibilities without a concrete reason.

---

# 6. Workflow Execution Architecture

Implement the following workflow.

```text
                  USER REQUEST
                       |
                       v
                API GATEWAY
                       |
                       v
                 ORCHESTRATOR
                       |
                       v
                PLANNER AGENT
                       |
                       v
                TASK DECOMPOSITION
                       |
                       v
                AGENT DISCOVERY
                       |
              +--------+--------+
              |                 |
              v                 v
        RESEARCH AGENT     ANALYST AGENT
              |                 |
              v                 |
           MCP TOOLS             |
              |                 |
              +--------+--------+
                       |
                       v
                RESULT AGGREGATION
                       |
                       v
                  WRITER AGENT
                       |
                       v
                 FINAL RESPONSE
```

Important:

- Use A2A for communication with independent A2A agents.
- Use MCP for tool and resource access.
- Use LangGraph for workflow state and execution where appropriate.
- Use Redis/PostgreSQL for state persistence.
- Use asynchronous execution for independent tasks.

Do not force every internal function call through A2A. Use protocol communication at actual agent boundaries.

---

# 7. API Requirements

Implement REST APIs through FastAPI.

### Agent APIs

```text
POST   /api/v1/agents/register
GET    /api/v1/agents
GET    /api/v1/agents/{agent_id}
GET    /api/v1/agents/discover
DELETE /api/v1/agents/{agent_id}
```

### Workflow APIs

```text
POST   /api/v1/workflows
GET    /api/v1/workflows
GET    /api/v1/workflows/{workflow_id}
DELETE /api/v1/workflows/{workflow_id}
```

### Execution APIs

```text
POST /api/v1/executions
GET  /api/v1/executions
GET  /api/v1/executions/{execution_id}
GET  /api/v1/executions/{execution_id}/status
```

### Health APIs

```text
GET /health
GET /health/agents
GET /health/dependencies
```

Use appropriate HTTP status codes, request validation, response schemas, and error handling.

---

# 8. Engineering Standards

These rules are mandatory.

### Python Standards

- Follow PEP 8.
- Use type hints.
- Use Pydantic for external data validation.
- Use async/await for I/O-bound operations.
- Use dependency injection where appropriate.
- Use modular services.
- Avoid circular imports.
- Avoid unnecessarily large classes and functions.

### Architecture Standards

- Maintain separation of concerns.
- Avoid tight coupling between agents.
- Keep protocol implementations independent.
- Use interfaces or protocols for replaceable components.
- Keep LLM provider integrations abstracted.
- Avoid hardcoded agent endpoints.
- Use configuration-driven behavior.

### Error Handling

Implement:

- Connection timeouts.
- Execution timeouts.
- Retry policies.
- Exponential backoff.
- Circuit breakers where appropriate.
- Structured error responses.
- Failure isolation.
- Graceful shutdown.

Do not retry non-idempotent operations blindly.

### Security

Implement:

- Environment-based secrets.
- API authentication.
- Role-based authorization where needed.
- MCP tool permission controls.
- Input validation.
- Rate limiting.
- Audit logging.
- Secure inter-agent communication.
- SSRF protection for agent endpoints.
- Filesystem path restrictions.
- SQL query restrictions.

Never expose secrets in logs or source code.

Treat agent outputs and MCP responses as untrusted input.

---

# 9. Testing Requirements

Every major component must have tests.

### Unit Tests

Test:
- Agent registration.
- Agent discovery.
- Capability matching.
- Task scheduling.
- Workflow state transitions.
- Input validation.
- Error handling.

### Integration Tests

Test:
- A2A agent communication.
- MCP client-server communication.
- PostgreSQL integration.
- Redis integration.
- LLM provider integration.

Use mock providers where external APIs are unnecessary.

### End-to-End Tests

Test complete workflows:

1. User submits a request.
2. Planner generates subtasks.
3. Registry discovers agents.
4. Orchestrator delegates tasks.
5. Agents invoke MCP tools.
6. Agents return results.
7. Writer generates the final response.

The complete workflow must work without manual intervention.

---

# 10. Implementation Phases

Follow this sequence.

## Phase 1 — Foundation

- Initialize Python project.
- Configure dependencies.
- Set up FastAPI.
- Configure PostgreSQL.
- Configure Redis.
- Implement settings management.
- Implement structured logging.
- Set up Docker Compose.

Deliverable: Running backend infrastructure.

## Phase 2 — Agent Architecture

- Implement agent interfaces.
- Implement Planner Agent.
- Implement Research Agent.
- Implement Analyst Agent.
- Implement Writer Agent.
- Define agent input/output schemas.

Deliverable: Independently executable agents.

## Phase 3 — MCP Integration

- Implement MCP client manager.
- Build Search MCP Server.
- Build Filesystem MCP Server.
- Build Database MCP Server.
- Connect agents to MCP tools.
- Implement tool discovery and execution.

Deliverable: Agents can access external tools through MCP.

## Phase 4 — A2A Integration

- Integrate official A2A Python SDK.
- Implement agent endpoints.
- Publish Agent Cards.
- Implement task delegation.
- Implement task status handling.
- Test communication between separate agent processes.

Deliverable: Independently deployed agents can communicate using A2A.

## Phase 5 — Agent Registry

- Implement registration.
- Implement discovery.
- Implement capability matching.
- Implement agent health checks.
- Implement agent lifecycle management.

Deliverable: Dynamic agent discovery.

## Phase 6 — Orchestration Engine

- Implement task decomposition.
- Implement workflow execution.
- Implement task dependency management.
- Implement parallel execution.
- Implement result aggregation.
- Implement retries and failure handling.
- Implement persistent workflow state.

Deliverable: End-to-end multi-agent orchestration.

## Phase 7 — Production Engineering

- Authentication and authorization.
- Rate limiting.
- Audit logs.
- Distributed tracing.
- Token and cost tracking.
- Monitoring.
- Failure recovery.
- Docker deployment.

Deliverable: Production-oriented platform.

## Phase 8 — Dashboard

Build a React/Next.js dashboard.

Include:

- Agent registry.
- Agent details.
- Agent health.
- Workflow execution.
- Live execution status.
- Task history.
- Agent communication visualization.
- Performance metrics.
- Error logs.

Deliverable: Operational management interface.

---

# 11. Development Rules for the Coding Agent

You must follow these instructions throughout development.

1. First inspect the existing repository before creating or modifying files.
2. Never overwrite existing code without understanding its purpose.
3. Do not generate the entire project in one uncontrolled operation.
4. Implement the system phase by phase.
5. Before implementing a feature, explain its purpose and integration point.
6. Use official protocol SDKs instead of inventing protocol implementations.
7. Verify package names, APIs, and compatibility before installing dependencies.
8. Do not use deprecated APIs when maintained alternatives exist.
9. Every major component must have working implementation and tests.
10. Never leave critical functionality as placeholder code.
11. Do not create fake successful responses.
12. Never hardcode API keys, credentials, or endpoints.
13. Keep `.env.example` updated.
14. Update documentation when architecture or APIs change.
15. Run relevant tests after each implementation phase.
16. Fix existing test failures before moving to dependent phases.
17. Keep the README synchronized with actual functionality.
18. Do not introduce unnecessary abstractions or dependencies.
19. Prefer working, maintainable code over excessive architectural complexity.
20. Record important architectural decisions in documentation.

### Important Execution Rule

Do not attempt to implement all phases simultaneously.

For each phase:

1. Inspect the existing implementation.
2. Identify required changes.
3. Explain the implementation plan.
4. Implement the functionality.
5. Run tests.
6. Fix errors.
7. Update documentation.
8. Summarize completed work.
9. Identify the next phase.

Wait for approval before starting the next major phase unless explicitly instructed to execute the complete roadmap autonomously.

---

# 12. Definition of Done

AgentMesh is considered functionally complete when:

- Agents can register dynamically.
- Agents can discover other agents.
- Independent agents communicate using A2A.
- Agents access external tools through MCP.
- The orchestrator decomposes complex requests.
- Multiple agents execute tasks collaboratively.
- Independent tasks execute concurrently.
- Workflow states persist.
- Failed tasks are handled safely.
- Agent health can be monitored.
- Execution history is available.
- Token usage and execution latency are tracked.
- The platform can run through Docker Compose.
- Automated tests cover critical functionality.
- Documentation describes the actual implementation.

---

# 13. First Task: Repository Initialization

Start by inspecting the current repository.

Then:

1. Determine whether the repository is empty or already contains code.
2. Identify the existing project structure.
3. Check the installed Python version.
4. Check available development tools.
5. Identify existing dependencies.
6. Create a concise implementation plan.
7. Propose the initial directory structure.
8. Identify potential architectural risks.
9. Begin Phase 1 only after presenting the plan.

Do not jump directly into implementing all agents.

The first milestone is a clean, runnable, well-structured Python backend.

---

# Final Instruction

Your responsibility is to act as a senior Python backend engineer, AI infrastructure engineer, and distributed systems architect.

Build AgentMesh as a maintainable, protocol-driven distributed agent platform.

Prioritize correctness, reliability, modularity, security, and observability over flashy demonstrations.

Every implemented feature must solve a real architectural requirement.

**The goal is not to demonstrate that multiple AI agents can talk to each other. The goal is to engineer infrastructure that allows independent AI agents to collaborate reliably at scale.**