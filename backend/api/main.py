"""FastAPI application factory, middleware, and lifecycle management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import time
import uuid

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.api.routes.health import router as health_router
from backend.config.settings import Settings, get_settings
from backend.infrastructure.database import DatabaseManager
from backend.infrastructure.logging import (
    configure_logging,
    get_correlation_id,
    get_logger,
    reset_correlation_id,
    set_correlation_id,
)
from backend.infrastructure.redis import RedisManager
from backend.infrastructure.telemetry import configure_telemetry

logger = get_logger(__name__)

CORRELATION_HEADER = b"x-correlation-id"


class CorrelationIdMiddleware:
    """ASGI middleware that propagates X-Correlation-ID and logs HTTP requests."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming_id: str | None = None
        for name, value in scope.get("headers", ()):
            if name.lower() == CORRELATION_HEADER:
                decoded = value.decode("latin-1").strip()
                if decoded:
                    incoming_id = decoded
                break

        correlation_id = incoming_id or str(uuid.uuid4())
        token = set_correlation_id(correlation_id)
        start = time.perf_counter()
        status_code = 500

        async def send_with_correlation(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", ()))
                headers.append((CORRELATION_HEADER, correlation_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_correlation)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "HTTP request completed",
                extra={
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
            reset_correlation_id(token)


def create_app(
    settings: Settings | None = None,
    db_manager: DatabaseManager | None = None,
    redis_manager: RedisManager | None = None,
) -> FastAPI:
    """Create and configure the AgentMesh FastAPI application."""
    resolved_settings = settings or get_settings()
    configure_logging(
        log_level=resolved_settings.log_level,
        log_format=resolved_settings.log_format,
    )
    configure_telemetry(resolved_settings)

    owns_db = db_manager is None
    owns_redis = redis_manager is None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        active_db = db_manager or DatabaseManager(resolved_settings)
        active_redis = redis_manager or RedisManager(resolved_settings)

        app.state.settings = resolved_settings
        app.state.db_manager = active_db
        app.state.redis_manager = active_redis

        logger.info(
            "AgentMesh backend starting",
            extra={
                "environment": resolved_settings.environment,
                "version": resolved_settings.app_version,
            },
        )
        try:
            yield
        finally:
            logger.info("AgentMesh backend shutting down")
            if owns_redis:
                await active_redis.close()
            if owns_db:
                await active_db.dispose()

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        debug=resolved_settings.debug,
        lifespan=lifespan,
    )

    app.state.settings = resolved_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "Unhandled server exception",
            extra={"path": request.url.path, "error_type": type(exc).__name__},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An unexpected internal error occurred.",
                "correlation_id": get_correlation_id(),
            },
        )

    app.include_router(health_router)
    return app

