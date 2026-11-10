"""Application settings loaded from environment variables and `.env`."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, environment-driven configuration for AgentMesh."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="AgentMesh", min_length=1)
    app_version: str = Field(default="0.1.0", min_length=1)
    environment: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "text"] = "json"

    # PostgreSQL / SQLAlchemy
    database_url: str = Field(
        default="postgresql+asyncpg://agentmesh:agentmesh@localhost:5432/agentmesh",
        min_length=1,
    )
    db_pool_size: int = Field(default=5, ge=1, le=100)
    db_max_overflow: int = Field(default=10, ge=0, le=100)
    db_echo: bool = False
    db_connect_timeout: float = Field(default=5.0, gt=0.0, le=60.0)

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", min_length=1)
    redis_socket_timeout: float = Field(default=3.0, gt=0.0, le=60.0)
    redis_connect_timeout: float = Field(default=3.0, gt=0.0, le=60.0)

    # CORS
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"]
    )

    # OpenTelemetry
    otel_enabled: bool = False
    otel_service_name: str = "agentmesh-backend"
    otel_exporter_otlp_endpoint: str | None = None

    # LLM Providers
    llm_provider: Literal["mock", "openai", "anthropic"] = "mock"
    llm_model: str = "gpt-4o-mini"
    llm_timeout: float = Field(default=30.0, gt=0.0, le=300.0)
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    openai_api_key: SecretStr | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: SecretStr | None = None
    anthropic_base_url: str = "https://api.anthropic.com/v1"

    # Security & Registry
    allow_private_agent_endpoints: bool = False
    agent_health_check_timeout: float = Field(default=3.0, gt=0.0, le=30.0)
    agent_registry_cache_ttl: int = Field(default=60, ge=1, le=3600)

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        return value.upper() if isinstance(value, str) else value

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        allowed_prefixes = (
            "postgresql+asyncpg://",
            "postgresql://",
            "sqlite+aiosqlite://",
        )
        if not value.startswith(allowed_prefixes):
            raise ValueError(
                "database_url must use an async-compatible PostgreSQL or SQLite URL"
            )
        return value

    @field_validator("redis_url")
    @classmethod
    def _validate_redis_url(cls, value: str) -> str:
        if not value.startswith(("redis://", "rediss://", "unix://")):
            raise ValueError("redis_url must start with redis://, rediss://, or unix://")
        return value

    @property
    def is_sqlite(self) -> bool:
        """Return True when configured with a SQLite database backend."""
        return self.database_url.startswith("sqlite")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()

