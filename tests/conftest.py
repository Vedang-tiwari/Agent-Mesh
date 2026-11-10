"""Shared pytest fixtures for AgentMesh tests."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import httpx
import pytest

from backend.api.main import create_app
from backend.config.settings import Settings
from backend.infrastructure.database import DatabaseManager
from backend.infrastructure.redis import RedisManager


@pytest.fixture
def test_settings() -> Settings:
    """Return isolated test settings backed by in-memory SQLite."""
    return Settings(
        environment="test",
        log_level="DEBUG",
        log_format="json",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/15",
        otel_enabled=False,
    )


@pytest.fixture
async def db_manager(test_settings: Settings) -> AsyncIterator[DatabaseManager]:
    """Provide an initialized DatabaseManager backed by in-memory SQLite."""
    manager = DatabaseManager(test_settings)
    try:
        yield manager
    finally:
        await manager.dispose()


@pytest.fixture
def fake_redis_client() -> AsyncMock:
    """Provide an async mock Redis client."""
    client = AsyncMock()
    client.ping = AsyncMock(return_value=True)
    client.aclose = AsyncMock(return_value=None)
    return client


@pytest.fixture
def redis_manager(
    test_settings: Settings, fake_redis_client: AsyncMock
) -> RedisManager:
    """Provide a RedisManager backed by a mock async Redis client."""
    return RedisManager(test_settings, client=fake_redis_client)


@pytest.fixture
async def async_client(
    test_settings: Settings,
    db_manager: DatabaseManager,
    redis_manager: RedisManager,
) -> AsyncIterator[httpx.AsyncClient]:
    """Provide an AsyncClient wired to the FastAPI app with active lifespan."""
    app = create_app(
        settings=test_settings,
        db_manager=db_manager,
        redis_manager=redis_manager,
    )
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            yield client

