"""Unit tests for configuration and settings validation."""

import pytest
from pydantic import ValidationError

from backend.config.settings import Settings


def test_settings_defaults() -> None:
    """Verify default configuration values are sane."""
    settings = Settings()
    assert settings.app_name == "AgentMesh"
    assert settings.environment == "development"
    assert settings.port == 8000
    assert settings.is_sqlite is False


def test_settings_normalizes_log_level() -> None:
    """Verify lowercase log levels are normalized to uppercase."""
    settings = Settings(log_level="debug")
    assert settings.log_level == "DEBUG"


def test_settings_sqlite_detection() -> None:
    """Verify SQLite URLs are detected accurately."""
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    assert settings.is_sqlite is True


def test_settings_rejects_invalid_database_url() -> None:
    """Verify unsupported database URL schemes raise ValidationError."""
    with pytest.raises(ValidationError):
        Settings(database_url="mysql://user:pass@localhost/db")


def test_settings_rejects_invalid_redis_url() -> None:
    """Verify invalid Redis URL schemes raise ValidationError."""
    with pytest.raises(ValidationError):
        Settings(redis_url="http://localhost:6379/0")

