"""Unit tests for agent endpoint SSRF protection."""

import pytest

from backend.core.security import UnsafeEndpointError, validate_agent_endpoint


def test_validate_agent_endpoint_allows_public_https() -> None:
    """Verify valid public HTTPS endpoints pass and strip trailing slash."""
    cleaned = validate_agent_endpoint("https://agents.example.com/a2a/")
    assert cleaned == "https://agents.example.com/a2a"


def test_validate_agent_endpoint_blocks_unsafe_schemes_and_credentials() -> None:
    """Verify non-HTTP schemes and embedded credentials are rejected."""
    with pytest.raises(UnsafeEndpointError, match="http or https"):
        validate_agent_endpoint("ftp://agents.example.com")

    with pytest.raises(UnsafeEndpointError, match="credentials"):
        validate_agent_endpoint("https://user:pass@agents.example.com")


def test_validate_agent_endpoint_blocks_metadata_and_private_ips() -> None:
    """Verify cloud metadata and private/loopback endpoints are blocked by default."""
    for blocked in (
        "http://169.254.169.254/latest/meta-data",
        "http://metadata.google.internal/computeMetadata/v1",
        "http://127.0.0.1:8001",
        "http://10.0.0.5:8001",
        "http://192.168.1.10:8001",
        "http://localhost:8001",
    ):
        with pytest.raises(UnsafeEndpointError):
            validate_agent_endpoint(blocked, allow_private=False)


def test_validate_agent_endpoint_allows_private_in_dev_but_never_metadata() -> None:
    """Verify allow_private permits localhost/private IPs but still blocks metadata."""
    assert (
        validate_agent_endpoint("http://localhost:8001/", allow_private=True)
        == "http://localhost:8001"
    )
    assert (
        validate_agent_endpoint("http://127.0.0.1:8001", allow_private=True)
        == "http://127.0.0.1:8001"
    )
    with pytest.raises(UnsafeEndpointError, match="metadata"):
        validate_agent_endpoint("http://169.254.169.254", allow_private=True)

