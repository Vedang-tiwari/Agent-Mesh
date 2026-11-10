# AgentMesh Architecture & Decisions

## Overview

AgentMesh separates platform infrastructure, workflow orchestration, agent-to-agent communication (A2A), and external tool access (MCP) into cleanly isolated layers.

## Implemented Layers (Phases 1–2)

| Layer | Module | Responsibility |
|---|---|---|
| Configuration | `backend/config/settings.py` | Typed environment-driven `Settings` via `pydantic-settings` |
| API Gateway | `backend/api/main.py`, `backend/api/routes/health.py` | FastAPI factory, ASGI `CorrelationIdMiddleware`, lifespan, health APIs |
| Database | `backend/infrastructure/database.py`, `backend/alembic/` | Async SQLAlchemy 2.0 engine/sessions, Alembic async migrations |
| Cache / State | `backend/infrastructure/redis.py` | Async Redis client pool, timeout-bounded health probe |
| Observability | `backend/infrastructure/logging.py`, `backend/infrastructure/telemetry.py` | Structured JSON/text logs with `correlation_id`/`workflow_id`, OpenTelemetry tracer setup |
| Schemas | `backend/schemas/` | `AgentIdentity`, `SubTask`, `TaskResult`, DAG-validated `ExecutionPlan`, agent I/O models |
| LLM Abstraction | `backend/agents/base/llm.py` | Provider-agnostic `LLMProvider` interface (`mock`, `openai`, `anthropic`) + usage/cost tracking |
| Agents | `backend/agents/` | `BaseAgent`, `PlannerAgent`, `ResearchAgent`, `AnalystAgent`, `WriterAgent` |

## Architectural Decision Records (ADRs)

### ADR-001: FastAPI Application Factory with Injected Managers
- **Decision**: `create_app(settings, db_manager, redis_manager)` accepts optional pre-built infrastructure managers and stores active managers on `app.state`.
- **Rationale**: Allows production `backend.main:app` to own and dispose DB/Redis pools cleanly in `lifespan`, while tests can inject isolated SQLite or mock dependencies without monkeypatching globals.

### ADR-002: Pure ASGI Middleware for Correlation IDs
- **Decision**: Implemented `CorrelationIdMiddleware` as a pure ASGI middleware instead of Starlette's `BaseHTTPMiddleware`.
- **Rationale**: Avoids `BaseHTTPMiddleware` task/context isolation quirks and preserves streaming/SSE compatibility needed by A2A/LangGraph in later phases while cleanly propagating `correlation_id` through `contextvars`.

### ADR-003: Dual Async Dialect Support (`asyncpg` + `aiosqlite`)
- **Decision**: Support `postgresql+asyncpg://` for runtime/Docker and `sqlite+aiosqlite://` for unit tests and lightweight local checks.
- **Rationale**: Enables fast, zero-external-service unit tests in CI/offline environments while keeping production SQLAlchemy 2.0 async semantics intact.

