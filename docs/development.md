# AgentMesh Development Guide

## Prerequisites

- Python 3.11+ (verified on Python 3.12.8)
- Docker & Docker Compose (for PostgreSQL 16 and Redis 7)

## Environment Variables

See `.env.example` for all supported configuration variables. Key settings:

- `DATABASE_URL`: Async SQLAlchemy URL (`postgresql+asyncpg://...` or `sqlite+aiosqlite://...`).
- `REDIS_URL`: Redis connection URL (`redis://localhost:6379/0`).
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.
- `LOG_FORMAT`: `json` (default, structured) or `text` (human-readable local dev).
- `OTEL_ENABLED`: `false` by default; enables OpenTelemetry `TracerProvider` when `opentelemetry-sdk` is installed.

## Running Tests

```bash
pytest
```

Tests run against an in-memory `sqlite+aiosqlite` database and mocked async Redis client so they execute deterministically without external services.

## Database Migrations (Alembic)

Alembic is configured for async SQLAlchemy migrations in `alembic.ini` and `backend/alembic/env.py`.

```bash
# Generate a migration once ORM models are added (Phases 5-6)
alembic revision --autogenerate -m "describe change"

# Apply migrations
alembic upgrade head
```

