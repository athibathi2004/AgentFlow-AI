"""Model Context Protocol (MCP) data schemas conforming to JSON-RPC 2.0 specification."""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class MCPToolDefinition(BaseModel):
    """Schema representing an exposed tool in MCP."""

    name: str = Field(..., description="Unique tool name")
    description: Optional[str] = Field(default=None, description="Human-readable tool description")
    inputSchema: Dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}},
        description="JSON Schema defining acceptable arguments",
    )


class MCPListToolsResponse(BaseModel):
    """Result for tools/list MCP method."""

    tools: List[MCPToolDefinition] = Field(default_factory=list)


class MCPTextContent(BaseModel):
    """Text-based content item returned by MCP tool execution."""

    type: Literal["text"] = "text"
    text: str


class MCPCallToolResult(BaseModel):
    """Result returned by tools/call execution."""

    content: List[Union[MCPTextContent, Dict[str, Any]]] = Field(default_factory=list)
    isError: bool = False


class MCPRequest(BaseModel):
    """JSON-RPC 2.0 request envelope for MCP."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: Union[str, int]
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """JSON-RPC 2.0 response envelope for MCP."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: Union[str, int]
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPServerConfig(BaseModel):
    """Configuration for an upstream MCP server."""

    id: str
    name: str
    transport: Literal["in_memory", "stdio", "sse"] = "in_memory"
    endpoint_url: Optional[str] = None
    enabled: bool = True
    description: Optional[str] = None

