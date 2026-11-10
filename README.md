# AgentMesh

**AgentMesh** is a Python-based distributed multi-agent orchestration platform engineered as reusable software infrastructure built around **FastAPI**, **LangGraph**, **A2A (Agent2Agent)**, **MCP (Model Context Protocol)**, **PostgreSQL**, **Redis**, and **OpenTelemetry**.

## Current Status: Phase 2 — Agent Architecture

Implemented in Phase 1 (Foundation):
- **FastAPI Backend** (`backend/api/main.py`, `backend/main.py`) with lifespan resource management, CORS, and structured error handling.
- **Configuration Management** (`backend/config/settings.py`) powered by `pydantic-settings` and `.env.example`.
- **Async PostgreSQL & Alembic** (`backend/infrastructure/database.py`, `alembic.ini`, `backend/alembic/`) using SQLAlchemy 2.0 `AsyncEngine` (with `sqlite+aiosqlite` support for isolated local/unit testing).
- **Async Redis Manager** (`backend/infrastructure/redis.py`) with timeout-guarded health checks and graceful shutdown.
- **Structured Logging & Correlation Context** (`backend/infrastructure/logging.py`) with JSON/text formatters, `correlation_id`/`workflow_id` `contextvars`, and `CorrelationIdMiddleware` propagating `X-Correlation-ID`.
- **OpenTelemetry Scaffold** (`backend/infrastructure/telemetry.py`) supporting configurable tracing.
- **Health Endpoints** (`backend/api/routes/health.py`):
  - `GET /health` — Service liveness
  - `GET /health/dependencies` — Concurrent PostgreSQL & Redis readiness (`200` healthy / `503` degraded)
  - `GET /health/agents` — Agent health summary (populated in Phase 5)
- **Containerization** (`docker/Dockerfile`, `docker-compose.yml`) for PostgreSQL 16, Redis 7, and the FastAPI backend.

Implemented in Phase 2 (Agent Architecture):
- **Typed Domain Schemas** (`backend/schemas/agent.py`, `backend/schemas/task.py`, `backend/schemas/workflow.py`) including `AgentIdentity`, `SubTask`, `TaskResult`, DAG-validated `ExecutionPlan`, and typed I/O contracts for all agents.
- **LLM Provider Abstraction** (`backend/agents/base/llm.py`) with `LLMProvider` protocol, `MockLLMProvider`, `OpenAICompatibleLLMProvider`, `AnthropicLLMProvider`, token/cost estimation, and `SecretStr`-protected settings.
- **Base Agent Lifecycle** (`backend/agents/base/agent.py`) providing `BaseAgent` with Pydantic I/O validation, correlation/workflow context propagation, OpenTelemetry spans, latency/token metrics, and `ToolInvoker` hook for Phase 3 MCP.
- **Specialized Agents**:
  - `PlannerAgent` (`backend/agents/planner/agent.py`)
  - `ResearchAgent` (`backend/agents/researcher/agent.py`)
  - `AnalystAgent` (`backend/agents/analyst/agent.py`)
  - `WriterAgent` (`backend/agents/writer/agent.py`)

## Quick Start

### Local Python Run (with SQLite fallback or local Postgres/Redis)

1. Copy `.env.example` to `.env` and adjust values if needed:
   ```bash
   cp .env.example .env
   ```
2. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
3. Run the API server:
   ```bash
   uvicorn backend.main:app --reload
   ```
4. Run unit tests:
   ```bash
   pytest
   ```

### Docker Compose

```bash
docker compose up --build
```

Verify health:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/dependencies
```

## Roadmap

1. **Phase 1 — Foundation** *(Complete)*
2. **Phase 2 — Agent Architecture** *(Complete)*
3. **Phase 3 — MCP Integration** *(Next)*
4. **Phase 4 — A2A Integration**
5. **Phase 5 — Agent Registry**
6. **Phase 6 — Orchestration Engine**
7. **Phase 7 — Production Engineering**
8. **Phase 8 — Dashboard**

