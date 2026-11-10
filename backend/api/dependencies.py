"""FastAPI dependency providers for AgentMesh."""

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import Settings
from backend.infrastructure.database import DatabaseManager
from backend.infrastructure.redis import RedisManager


def get_app_settings(request: Request) -> Settings:
    """Retrieve application settings stored on app state."""
    return request.app.state.settings


def get_database_manager(request: Request) -> DatabaseManager:
    """Retrieve the DatabaseManager stored on app state."""
    return request.app.state.db_manager


def get_redis_manager(request: Request) -> RedisManager:
    """Retrieve the RedisManager stored on app state."""
    return request.app.state.redis_manager


async def get_db_session(
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> AsyncIterator[AsyncSession]:
    """Yield an async database session for request handlers."""
    async with db_manager.session() as session:
        yield session

