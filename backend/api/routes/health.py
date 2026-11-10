"""Health check endpoints for service, dependencies, and agents."""

import asyncio
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from backend.api.dependencies import (
    get_app_settings,
    get_database_manager,
    get_redis_manager,
)
from backend.config.settings import Settings
from backend.infrastructure.database import DatabaseManager, HealthCheckResult
from backend.infrastructure.redis import RedisManager

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    """Basic liveness response."""

    status: Literal["healthy"]
    service: str
    version: str
    environment: str
    timestamp: datetime


class DependencyStatus(BaseModel):
    """Health check status for a single external dependency."""

    status: Literal["healthy", "unhealthy"]
    latency_ms: float
    detail: str | None = None


class DependenciesHealthResponse(BaseModel):
    """Aggregated readiness response across infrastructure dependencies."""

    status: Literal["healthy", "degraded"]
    timestamp: datetime
    dependencies: dict[str, DependencyStatus]


class AgentHealthSummary(BaseModel):
    """Individual agent health record (populated once Registry is active)."""

    agent_id: str
    name: str
    status: str


class AgentsHealthResponse(BaseModel):
    """Agent fleet health summary."""

    status: Literal["ok"]
    timestamp: datetime
    total_agents: int
    healthy_agents: int
    agents: list[AgentHealthSummary]


def _to_dependency_status(result: HealthCheckResult) -> DependencyStatus:
    return DependencyStatus(
        status="healthy" if result.healthy else "unhealthy",
        latency_ms=result.latency_ms,
        detail=result.detail,
    )


@router.get("", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check(
    settings: Settings = Depends(get_app_settings),
) -> HealthResponse:
    """Return service liveness metadata."""
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(UTC),
    )


@router.get("/dependencies", response_model=DependenciesHealthResponse)
async def dependencies_health_check(
    response: Response,
    db_manager: DatabaseManager = Depends(get_database_manager),
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> DependenciesHealthResponse:
    """Probe PostgreSQL and Redis readiness concurrently."""
    db_result, redis_result = await asyncio.gather(
        db_manager.check_health(),
        redis_manager.check_health(),
    )
    all_healthy = db_result.healthy and redis_result.healthy
    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return DependenciesHealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.now(UTC),
        dependencies={
            "database": _to_dependency_status(db_result),
            "redis": _to_dependency_status(redis_result),
        },
    )


@router.get("/agents", response_model=AgentsHealthResponse, status_code=status.HTTP_200_OK)
async def agents_health_check() -> AgentsHealthResponse:
    """Return registered agent health summary (empty until Phase 5 Registry)."""
    return AgentsHealthResponse(
        status="ok",
        timestamp=datetime.now(UTC),
        total_agents=0,
        healthy_agents=0,
        agents=[],
    )

