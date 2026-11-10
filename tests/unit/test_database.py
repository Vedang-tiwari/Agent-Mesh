"""Unit tests for DatabaseManager and RedisManager infrastructure."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text

from backend.config.settings import Settings
from backend.infrastructure.database import DatabaseManager
from backend.infrastructure.redis import RedisManager


async def test_database_health_check_succeeds(db_manager: DatabaseManager) -> None:
    """Verify SELECT 1 health probe succeeds on SQLite async engine."""
    result = await db_manager.check_health()
    assert result.healthy is True
    assert result.latency_ms >= 0.0
    assert result.detail is None


async def test_database_session_executes_query(db_manager: DatabaseManager) -> None:
    """Verify async session executes queries and rolls back on exception."""
    async with db_manager.session() as session:
        value = await session.scalar(text("SELECT 42"))
        assert value == 42

    with pytest.raises(RuntimeError, match="boom"):
        async with db_manager.session() as session:
            await session.execute(text("SELECT 1"))
            raise RuntimeError("boom")


async def test_database_health_check_handles_failure(test_settings: Settings) -> None:
    """Verify database health check reports unhealthy without raising."""
    manager = DatabaseManager(test_settings)
    await manager.dispose()
    manager.engine.connect = lambda: (_ for _ in ()).throw(ConnectionError("refused"))  # type: ignore[method-assign]

    result = await manager.check_health()
    assert result.healthy is False
    assert "ConnectionError" in (result.detail or "")


async def test_redis_health_check_succeeds(redis_manager: RedisManager) -> None:
    """Verify Redis health probe succeeds when PING returns True."""
    result = await redis_manager.check_health()
    assert result.healthy is True
    assert result.detail is None


async def test_redis_health_check_handles_failure(test_settings: Settings) -> None:
    """Verify Redis health probe reports unhealthy when client raises."""
    broken_client = AsyncMock()
    broken_client.ping = AsyncMock(side_effect=TimeoutError("timed out"))
    manager = RedisManager(test_settings, client=broken_client)

    result = await manager.check_health()
    assert result.healthy is False
    assert "TimeoutError" in (result.detail or "")

