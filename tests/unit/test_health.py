"""Unit tests for FastAPI health endpoints and correlation middleware."""

from unittest.mock import AsyncMock

import httpx

from backend.api.main import create_app
from backend.config.settings import Settings
from backend.infrastructure.database import DatabaseManager, HealthCheckResult
from backend.infrastructure.redis import RedisManager


async def test_health_endpoint_returns_healthy(async_client: httpx.AsyncClient) -> None:
    """Verify GET /health returns 200 and service metadata."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "AgentMesh"
    assert body["environment"] == "test"
    assert "x-correlation-id" in response.headers


async def test_correlation_id_is_propagated(async_client: httpx.AsyncClient) -> None:
    """Verify incoming X-Correlation-ID header is echoed back."""
    response = await async_client.get(
        "/health",
        headers={"X-Correlation-ID": "req-xyz-789"},
    )
    assert response.status_code == 200
    assert response.headers["x-correlation-id"] == "req-xyz-789"


async def test_health_agents_endpoint(async_client: httpx.AsyncClient) -> None:
    """Verify GET /health/agents returns empty summary before Phase 5."""
    response = await async_client.get("/health/agents")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["total_agents"] == 0
    assert body["healthy_agents"] == 0
    assert body["agents"] == []


async def test_health_dependencies_all_healthy(
    async_client: httpx.AsyncClient,
) -> None:
    """Verify GET /health/dependencies returns 200 when DB and Redis are healthy."""
    response = await async_client.get("/health/dependencies")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["dependencies"]["database"]["status"] == "healthy"
    assert body["dependencies"]["redis"]["status"] == "healthy"


async def test_health_dependencies_returns_503_when_redis_unhealthy(
    test_settings: Settings,
    db_manager: DatabaseManager,
) -> None:
    """Verify GET /health/dependencies returns 503 when Redis is unreachable."""
    failing_redis = AsyncMock(spec=RedisManager)
    failing_redis.check_health = AsyncMock(
        return_value=HealthCheckResult(
            healthy=False,
            latency_ms=5.0,
            detail="Redis unreachable (ConnectionError)",
        )
    )
    app = create_app(
        settings=test_settings,
        db_manager=db_manager,
        redis_manager=failing_redis,
    )
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            response = await client.get("/health/dependencies")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["database"]["status"] == "healthy"
    assert body["dependencies"]["redis"]["status"] == "unhealthy"

