"""Async SQLAlchemy database engine, session factory, and health checks."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
import time

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.config.settings import Settings
from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base class for all AgentMesh ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


@dataclass(frozen=True, slots=True)
class HealthCheckResult:
    """Result of an infrastructure dependency health probe."""

    healthy: bool
    latency_ms: float
    detail: str | None = None


def create_engine_from_settings(settings: Settings) -> AsyncEngine:
    """Create a configured SQLAlchemy AsyncEngine for PostgreSQL or SQLite."""
    if settings.is_sqlite:
        return create_async_engine(
            settings.database_url,
            echo=settings.db_echo,
        )

    return create_async_engine(
        settings.database_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        connect_args={"timeout": settings.db_connect_timeout},
    )


class DatabaseManager:
    """Manages the async SQLAlchemy engine and session lifecycle."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.engine: AsyncEngine = create_engine_from_settings(settings)
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield an async database session with automatic rollback on error."""
        async with self.session_factory() as db_session:
            try:
                yield db_session
            except Exception:
                await db_session.rollback()
                raise

    async def check_health(self, timeout: float | None = None) -> HealthCheckResult:
        """Verify database connectivity by executing SELECT 1 within timeout."""
        effective_timeout = timeout or self._settings.db_connect_timeout
        start = time.perf_counter()
        try:
            async with asyncio.timeout(effective_timeout):
                async with self.engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return HealthCheckResult(healthy=True, latency_ms=latency_ms)
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.warning(
                "Database health check failed",
                extra={"error_type": type(exc).__name__, "latency_ms": latency_ms},
            )
            return HealthCheckResult(
                healthy=False,
                latency_ms=latency_ms,
                detail=f"Database unreachable ({type(exc).__name__})",
            )

    async def dispose(self) -> None:
        """Dispose the underlying connection pool cleanly."""
        await self.engine.dispose()
        logger.info("Database engine disposed")

