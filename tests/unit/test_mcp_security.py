"""Unit tests for Phase 3 MCP models, security guards, and tool backends."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.protocols.mcp.models import (
    MCPServerConfig,
    MCPToolCallRequest,
    MCPToolCallResult,
    MCPTransportType,
)
from backend.protocols.mcp.security import (
    FilesystemPathGuard,
    MCPPermissionDeniedError,
    MCPPermissionPolicy,
    MCPSecurityError,
    SQLQueryGuard,
)
from backend.protocols.mcp.tools import FilesystemToolBackend


def test_mcp_server_config_validates_transport_fields() -> None:
    """Verify stdio requires command and HTTP/SSE requires url."""
    cfg = MCPServerConfig(
        name="filesystem",
        transport=MCPTransportType.STDIO,
        command="python",
        args=["mcp_servers/filesystem_server.py"],
    )
    assert cfg.name == "filesystem"

    with pytest.raises(ValidationError, match="requires 'command'"):
        MCPServerConfig(name="broken", transport=MCPTransportType.STDIO)

    with pytest.raises(ValidationError, match="requires 'url'"):
        MCPServerConfig(name="broken-http", transport=MCPTransportType.STREAMABLE_HTTP)


def test_mcp_permission_policy_enforces_allow_and_deny() -> None:
    """Verify deny overrides allow and wildcard rules work."""
    policy = MCPPermissionPolicy(
        allowed_tools={"filesystem": {"read_file", "list_directory"}},
        denied_tools={"filesystem": {"read_file"}, "database": {"*"}},
        default_allow=False,
    )
    assert policy.is_allowed("filesystem", "list_directory") is True
    assert policy.is_allowed("filesystem", "read_file") is False
    assert policy.is_allowed("database", "execute_readonly_query") is False
    assert policy.is_allowed("search", "web_search") is False

    with pytest.raises(MCPPermissionDeniedError):
        policy.require_allowed("filesystem", "read_file")


def test_filesystem_path_guard_blocks_traversal_and_allows_nested(tmp_path: Path) -> None:
    """Verify path traversal, outside paths, and null bytes are rejected."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    sample = docs_dir / "note.txt"
    sample.write_text("hello agentmesh", encoding="utf-8")

    guard = FilesystemPathGuard(allowed_roots=[tmp_path], max_read_bytes=1024)
    assert guard.validate_path("docs/note.txt") == sample.resolve()

    with pytest.raises(MCPSecurityError):
        guard.validate_path("../outside.txt")

    with pytest.raises(MCPSecurityError):
        guard.validate_path("docs/note.txt\x00.png")


def test_filesystem_tool_backend_operations(tmp_path: Path) -> None:
    """Verify list_directory, read_file, and search_files obey size and path limits."""
    (tmp_path / "a.md").write_text("# Title", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.md").write_text("0123456789ABCDEF", encoding="utf-8")

    guard = FilesystemPathGuard(allowed_roots=[tmp_path], max_read_bytes=10)
    backend = FilesystemToolBackend(guard)

    entries = backend.list_directory(".")
    assert [e["name"] for e in entries] == ["a.md", "sub"]

    read_ok = backend.read_file("a.md")
    assert read_ok["content"] == "# Title"

    with pytest.raises(MCPSecurityError, match="max_read_bytes"):
        backend.read_file("sub/b.md")

    matches = backend.search_files("*.md")
    assert sorted(matches) == ["a.md", str(Path("sub") / "b.md")]

    with pytest.raises(MCPSecurityError):
        backend.search_files("../*.md")


def test_sql_query_guard_allows_select_and_blocks_mutations() -> None:
    """Verify SQLQueryGuard permits safe SELECT/WITH and blocks writes/multi-statements."""
    guard = SQLQueryGuard(allowed_tables={"agents", "workflows"})

    clean = guard.validate_query("SELECT agent_id, name FROM agents WHERE status = 'active';")
    assert clean.startswith("SELECT agent_id")

    cte = guard.validate_query(
        "WITH active AS (SELECT agent_id FROM agents) SELECT * FROM active"
    )
    assert cte.startswith("WITH active")

    with pytest.raises(MCPSecurityError, match="not permitted"):
        guard.validate_query("SELECT * FROM users")

    for dangerous in (
        "DROP TABLE agents",
        "DELETE FROM agents",
        "INSERT INTO agents VALUES ('x')",
        "SELECT * FROM agents; DROP TABLE agents",
        "SELECT * FROM agents -- comment\n; DELETE FROM agents",
        "PRAGMA table_info(agents)",
    ):
        with pytest.raises(MCPSecurityError):
            guard.validate_query(dangerous)


def test_mcp_call_models() -> None:
    """Verify MCPToolCallRequest and MCPToolCallResult models."""
    req = MCPToolCallRequest(
        server_name="filesystem",
        tool_name="read_file",
        arguments={"path": "README.md"},
    )
    res = MCPToolCallResult(
        server_name=req.server_name,
        tool_name=req.tool_name,
        success=True,
        content=[{"type": "text", "text": "ok"}],
        latency_ms=1.2,
    )
    assert res.success is True
