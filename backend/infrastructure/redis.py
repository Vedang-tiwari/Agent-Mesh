"""Async Redis client manager and health checks."""

import asyncio
import time

import redis.asyncio as aioredis

from backend.config.settings import Settings
from backend.infrastructure.database import HealthCheckResult
from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)


class RedisManager:
    """Manages the async Redis connection pool and health probes."""

    def __init__(
        self,
        settings: Settings,
        client: aioredis.Redis | None = None,
    ) -> None:
        self._settings = settings
        self.client: aioredis.Redis = client or aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=settings.redis_socket_timeout,
            socket_connect_timeout=settings.redis_connect_timeout,
        )

    async def check_health(self, timeout: float | None = None) -> HealthCheckResult:
        """Verify Redis connectivity via PING within timeout."""
        effective_timeout = timeout or self._settings.redis_socket_timeout
        start = time.perf_counter()
        try:
            async with asyncio.timeout(effective_timeout):
                pong = await self.client.ping()
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            if pong:
                return HealthCheckResult(healthy=True, latency_ms=latency_ms)
            return HealthCheckResult(
                healthy=False,
                latency_ms=latency_ms,
                detail="Redis PING returned falsy response",
            )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.warning(
                "Redis health check failed",
                extra={"error_type": type(exc).__name__, "latency_ms": latency_ms},
            )
            return HealthCheckResult(
                healthy=False,
                latency_ms=latency_ms,
                detail=f"Redis unreachable ({type(exc).__name__})",
            )

    async def close(self) -> None:
        """Close the async Redis client cleanly."""
        await self.client.aclose()
        logger.info("Redis client closed")

