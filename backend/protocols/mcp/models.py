"""Pydantic models for MCP server configurations, tool discovery, and invocation."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class MCPTransportType(StrEnum):
    """Supported MCP client-server transport mechanisms."""

    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable_http"
    SSE = "sse"


class MCPServerConfig(BaseModel):
    """Configuration describing an external or local MCP server connection."""

    name: str = Field(..., min_length=1, max_length=128)
    transport: MCPTransportType = MCPTransportType.STDIO
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str | None = None
    timeout_seconds: float = Field(default=15.0, gt=0.0, le=300.0)
    enabled: bool = True
    allowed_tools: list[str] | None = None

    @model_validator(mode="after")
    def _validate_transport_fields(self) -> "MCPServerConfig":
        if self.transport == MCPTransportType.STDIO and not self.command:
            raise ValueError("STDIO MCP server config requires 'command'")
        if self.transport in (
            MCPTransportType.STREAMABLE_HTTP,
            MCPTransportType.SSE,
        ) and not self.url:
            raise ValueError(f"{self.transport} MCP server config requires 'url'")
        return self


class MCPToolSpec(BaseModel):
    """Discovered MCP tool definition normalized for AgentMesh."""

    server_name: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)


class MCPToolCallRequest(BaseModel):
    """Structured request to invoke a tool on an MCP server."""

    server_name: str = Field(..., min_length=1)
    tool_name: str = Field(..., min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float | None = Field(default=None, gt=0.0, le=300.0)


class MCPToolCallResult(BaseModel):
    """Structured response returned from an MCP tool invocation."""

    server_name: str = Field(..., min_length=1)
    tool_name: str = Field(..., min_length=1)
    success: bool
    content: list[dict[str, Any]] = Field(default_factory=list)
    structured_content: dict[str, Any] | None = None
    error: str | None = None
    latency_ms: float = Field(default=0.0, ge=0.0)

