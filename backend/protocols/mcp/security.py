"""Security guards for MCP tool permissions, filesystem paths, and SQL queries."""

from pathlib import Path
import re


class MCPSecurityError(PermissionError):
    """Base exception for MCP security and sandboxing violations."""


class MCPPermissionDeniedError(MCPSecurityError):
    """Raised when an MCP tool call violates configured permission policy."""


class MCPPermissionPolicy:
    """Enforces allow/deny controls on MCP server tool invocations."""

    def __init__(
        self,
        allowed_tools: dict[str, set[str]] | None = None,
        denied_tools: dict[str, set[str]] | None = None,
        default_allow: bool = True,
    ) -> None:
        self._allowed = allowed_tools or {}
        self._denied = denied_tools or {}
        self._default_allow = default_allow

    def is_allowed(self, server_name: str, tool_name: str) -> bool:
        """Return True if the tool invocation is permitted by policy."""
        denied_for_server = self._denied.get(server_name, set())
        if "*" in denied_for_server or tool_name in denied_for_server:
            return False

        if server_name in self._allowed:
            allowed_for_server = self._allowed[server_name]
            return "*" in allowed_for_server or tool_name in allowed_for_server

        return self._default_allow

    def require_allowed(self, server_name: str, tool_name: str) -> None:
        """Raise MCPPermissionDeniedError if invocation is not permitted."""
        if not self.is_allowed(server_name, tool_name):
            raise MCPPermissionDeniedError(
                f"Tool '{tool_name}' on MCP server '{server_name}' is denied by policy"
            )


class FilesystemPathGuard:
    """Restricts filesystem operations to explicitly configured root directories."""

    def __init__(
        self,
        allowed_roots: list[Path | str],
        max_read_bytes: int = 1_048_576,
    ) -> None:
        if not allowed_roots:
            raise ValueError("FilesystemPathGuard requires at least one allowed root")
        self.allowed_roots = [Path(root).resolve() for root in allowed_roots]
        self.max_read_bytes = max_read_bytes

    def validate_path(self, requested_path: str | Path) -> Path:
        """Resolve and verify requested_path stays strictly inside allowed_roots."""
        raw = str(requested_path)
        if "\x00" in raw:
            raise MCPSecurityError("Null byte is not permitted in filesystem path")

        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = self.allowed_roots[0] / candidate

        resolved = candidate.resolve()
        for root in self.allowed_roots:
            if resolved == root or resolved.is_relative_to(root):
                return resolved

        raise MCPSecurityError(
            f"Access denied: path '{requested_path}' is outside allowed roots"
        )


_SQL_COMMENT_RE = re.compile(r"--.*?$|/\*.*?\*/", re.MULTILINE | re.DOTALL)
_FORBIDDEN_SQL_KEYWORDS_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|GRANT|REVOKE|"
    r"ATTACH|DETACH|VACUUM|REINDEX|MERGE|CALL|COPY|EXEC|EXECUTE|PRAGMA)\b",
    re.IGNORECASE,
)
_TABLE_REF_RE = re.compile(r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_.]*)", re.IGNORECASE)
_CTE_NAME_RE = re.compile(
    r"(?:\bWITH(?:\s+RECURSIVE)?|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s+AS\s*\(",
    re.IGNORECASE,
)


class SQLQueryGuard:
    """Validates SQL queries to enforce read-only, single-statement access."""

    def __init__(
        self,
        allowed_tables: set[str] | None = None,
        max_limit: int = 200,
    ) -> None:
        self.allowed_tables = (
            {t.lower() for t in allowed_tables} if allowed_tables else None
        )
        self.max_limit = max_limit

    def validate_query(self, sql: str) -> str:
        """Verify SQL is a single read-only SELECT/WITH query without forbidden ops."""
        stripped = sql.strip()
        if not stripped:
            raise MCPSecurityError("SQL query cannot be empty")

        no_comments = _SQL_COMMENT_RE.sub(" ", stripped).strip()
        # Allow a single trailing semicolon, forbid any embedded statement separator.
        normalized = no_comments.rstrip(";").strip()
        if ";" in normalized:
            raise MCPSecurityError("Multiple SQL statements are not permitted")

        upper_start = normalized.lstrip("(").upper()
        if not upper_start.startswith(("SELECT ", "WITH ")):
            raise MCPSecurityError(
                "Only read-only SELECT or WITH queries are permitted"
            )

        forbidden_match = _FORBIDDEN_SQL_KEYWORDS_RE.search(normalized)
        if forbidden_match:
            raise MCPSecurityError(
                f"Forbidden SQL keyword '{forbidden_match.group(1).upper()}' detected"
            )

        if self.allowed_tables is not None:
            cte_names = {
                match.group(1).lower() for match in _CTE_NAME_RE.finditer(normalized)
            }
            referenced = {
                match.group(1).lower()
                for match in _TABLE_REF_RE.finditer(normalized)
            }
            disallowed = referenced - self.allowed_tables - cte_names
            if disallowed:
                raise MCPSecurityError(
                    f"Access to table(s) {sorted(disallowed)} is not permitted"
                )

        return normalized
