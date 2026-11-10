"""Sandboxed tool backends ready to be exposed by Phase 3 MCP servers."""

from pathlib import Path
from typing import Any

from sqlalchemy import text

from backend.infrastructure.database import DatabaseManager
from backend.protocols.mcp.security import (
    FilesystemPathGuard,
    MCPSecurityError,
    SQLQueryGuard,
)


class FilesystemToolBackend:
    """Safe filesystem operations confined by FilesystemPathGuard."""

    def __init__(self, guard: FilesystemPathGuard) -> None:
        self.guard = guard

    def list_directory(self, path: str = ".") -> list[dict[str, Any]]:
        """List files and subdirectories inside a validated directory."""
        target = self.guard.validate_path(path)
        if not target.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        if not target.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {path}")

        entries: list[dict[str, Any]] = []
        for item in sorted(target.iterdir(), key=lambda p: p.name):
            entries.append(
                {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size_bytes": item.stat().st_size if item.is_file() else None,
                }
            )
        return entries

    def read_file(self, path: str, encoding: str = "utf-8") -> dict[str, Any]:
        """Read a UTF-8 text file within allowed roots and size limits."""
        target = self.guard.validate_path(path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not target.is_file():
            raise IsADirectoryError(f"Path is not a file: {path}")

        size = target.stat().st_size
        if size > self.guard.max_read_bytes:
            raise MCPSecurityError(
                f"File size ({size} bytes) exceeds max_read_bytes ({self.guard.max_read_bytes})"
            )

        content = target.read_text(encoding=encoding)
        return {
            "path": str(target),
            "size_bytes": size,
            "content": content,
        }

    def search_files(
        self, pattern: str, root: str = ".", max_results: int = 50
    ) -> list[str]:
        """Search for files matching a glob pattern inside an allowed directory."""
        if ".." in pattern or Path(pattern).is_absolute():
            raise MCPSecurityError("Search pattern must be a relative glob without '..'")
        base = self.guard.validate_path(root)
        if not base.is_dir():
            raise NotADirectoryError(f"Search root is not a directory: {root}")

        matches: list[str] = []
        for candidate in base.rglob(pattern):
            resolved = self.guard.validate_path(candidate)
            if resolved.is_file():
                matches.append(str(resolved.relative_to(base)))
                if len(matches) >= max_results:
                    break
        return matches


class DatabaseToolBackend:
    """Safe read-only database query backend guarded by SQLQueryGuard."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        guard: SQLQueryGuard,
    ) -> None:
        self.db_manager = db_manager
        self.guard = guard

    async def execute_readonly_query(
        self, sql: str, limit: int | None = None
    ) -> dict[str, Any]:
        """Validate and execute a read-only SQL query with bounded rows."""
        validated_sql = self.guard.validate_query(sql)
        effective_limit = min(limit or self.guard.max_limit, self.guard.max_limit)

        async with self.db_manager.session() as session:
            result = await session.execute(text(validated_sql))
            columns = list(result.keys())
            rows = result.fetchmany(effective_limit)

        records = [dict(zip(columns, row, strict=False)) for row in rows]
        return {
            "columns": columns,
            "row_count": len(records),
            "truncated": len(records) == effective_limit,
            "rows": records,
        }

