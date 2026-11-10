"""SSRF protection and endpoint validation for registered agent URLs."""

import ipaddress
from urllib.parse import urlparse


class UnsafeEndpointError(ValueError):
    """Raised when an agent endpoint URL fails SSRF or scheme validation."""


_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
        "metadata",
    }
)


def validate_agent_endpoint(url: str, allow_private: bool = False) -> str:
    """Validate an agent endpoint URL and guard against SSRF attacks."""
    trimmed = url.strip()
    parsed = urlparse(trimmed)

    if parsed.scheme not in ("http", "https"):
        raise UnsafeEndpointError("Agent endpoint must use http or https scheme")
    if not parsed.netloc or not parsed.hostname:
        raise UnsafeEndpointError("Agent endpoint must include a valid hostname")
    if parsed.username or parsed.password:
        raise UnsafeEndpointError("Agent endpoint must not embed credentials")

    hostname = parsed.hostname.lower().rstrip(".")

    # Always block cloud instance metadata IPs/hosts regardless of environment.
    if hostname in ("169.254.169.254", "metadata.google.internal", "metadata"):
        raise UnsafeEndpointError(
            f"Agent endpoint host '{hostname}' is blocked (metadata service)"
        )

    try:
        ip_obj = ipaddress.ip_address(hostname)
    except ValueError:
        ip_obj = None

    if ip_obj is not None:
        if ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_unspecified:
            raise UnsafeEndpointError(
                f"Agent endpoint IP '{ip_obj}' is not permitted"
            )
        if not allow_private and (ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved):
            raise UnsafeEndpointError(
                f"Private or loopback agent endpoint IP '{ip_obj}' is blocked"
            )
    else:
        if not allow_private and (
            hostname in _BLOCKED_HOSTNAMES or hostname.endswith(".local")
        ):
            raise UnsafeEndpointError(
                f"Private or local agent hostname '{hostname}' is blocked"
            )

    return trimmed.rstrip("/")

