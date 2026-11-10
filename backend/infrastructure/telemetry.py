"""OpenTelemetry tracer configuration for AgentMesh."""

from opentelemetry import trace

from backend.config.settings import Settings
from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)


def configure_telemetry(settings: Settings) -> None:
    """Initialize OpenTelemetry tracing when enabled and SDK is available."""
    if not settings.otel_enabled:
        logger.info("OpenTelemetry tracing disabled by configuration")
        return

    try:
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
    except ImportError:
        logger.warning(
            "OTEL_ENABLED is true but opentelemetry-sdk is not installed; "
            "falling back to API no-op tracer"
        )
        return

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": settings.app_version,
            "deployment.environment": settings.environment,
        }
    )
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    logger.info(
        "OpenTelemetry TracerProvider configured",
        extra={"service_name": settings.otel_service_name},
    )


def get_tracer(name: str) -> trace.Tracer:
    """Return an OpenTelemetry tracer for the given module name."""
    return trace.get_tracer(name)

