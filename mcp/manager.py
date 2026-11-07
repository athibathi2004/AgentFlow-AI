"""Model Context Protocol (MCP) Connection Manager.

Oversees connection lifecycles, server discovery, and tool registration into ToolRegistry.
"""

from typing import Any, Dict, List, Optional
import httpx
from app.core.exceptions import MCPError
from app.core.logging import get_logger
from app.mcp.adapter import MCPToolAdapter
from app.mcp.schemas import (
    MCPCallToolResult,
    MCPServerConfig,
    MCPTextContent,
    MCPToolDefinition,
)
from app.tools.registry import ToolRegistry

logger = get_logger(__name__)


class MCPConnectionManager:
    """Manages external and simulated MCP server connections and lifecycle."""

    _instance: Optional["MCPConnectionManager"] = None

    def __init__(self) -> None:
        self._servers: Dict[str, MCPServerConfig] = {}
        self._server_health: Dict[str, bool] = {}
        self._registered_mcp_tools: Dict[str, List[str]] = {}  # server_id -> [tool_id]
        self._register_default_servers()

    @classmethod
    def get_instance(cls) -> "MCPConnectionManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _register_default_servers(self) -> None:
        """Register built-in reference MCP servers for zero-configuration testing."""
        self.register_server(
            MCPServerConfig(
                id="enterprise_kb",
                name="Enterprise Knowledge Base MCP",
                transport="in_memory",
                description="Simulated MCP server exposing internal vector database and enterprise doc queries",
                enabled=True,
            )
        )

    def register_server(self, config: MCPServerConfig) -> None:
        """Register an MCP server configuration."""
        self._servers[config.id] = config
        self._server_health[config.id] = config.enabled
        logger.info(f"Registered MCP server configuration: {config.id} ({config.name})")

    def unregister_server(self, server_id: str) -> None:
        """Disconnect and remove an MCP server, cleaning up registered tools."""
        if server_id in self._servers:
            registry = ToolRegistry.get_instance()
            for tool_id in self._registered_mcp_tools.get(server_id, []):
                registry.unregister(tool_id)
            del self._servers[server_id]
            self._server_health.pop(server_id, None)
            self._registered_mcp_tools.pop(server_id, None)

    async def list_servers(self) -> List[Dict[str, Any]]:
        """Return list of registered MCP servers with status."""
        results = []
        for server in self._servers.values():
            results.append({
                "id": server.id,
                "name": server.name,
                "transport": server.transport,
                "description": server.description,
                "enabled": server.enabled,
                "is_connected": self._server_health.get(server.id, False),
                "discovered_tools": self._registered_mcp_tools.get(server.id, []),
            })
        return results

    async def discover_tools(self, server_id: str) -> List[MCPToolDefinition]:
        """Discover tools exposed by a specific MCP server."""
        server = self._servers.get(server_id)
        if not server:
            raise MCPError(f"MCP server '{server_id}' is not configured")
        if not server.enabled:
            raise MCPError(f"MCP server '{server_id}' is disabled")

        if server.transport == "in_memory":
            return self._get_simulated_tools(server_id)
        elif server.transport in ("sse", "stdio"):
            if not server.endpoint_url:
                raise MCPError(f"Missing endpoint URL for remote MCP server '{server_id}'")
            return await self._discover_remote_tools(server)
        else:
            raise MCPError(f"Unsupported transport '{server.transport}' for MCP server '{server_id}'")

    def _get_simulated_tools(self, server_id: str) -> List[MCPToolDefinition]:
        """Return tool definitions for built-in in-memory MCP servers."""
        if server_id == "enterprise_kb":
            return [
                MCPToolDefinition(
                    name="query_knowledge_base",
                    description="Query corporate vector indices for compliance and infrastructure policy specs.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search prompt for enterprise policies",
                            },
                            "department": {
                                "type": "string",
                                "description": "Target department filter (e.g. 'security', 'compliance')",
                            },
                        },
                        "required": ["query"],
                    },
                )
            ]
        return []

    async def _discover_remote_tools(self, server: MCPServerConfig) -> List[MCPToolDefinition]:
        """Fetch tools/list via JSON-RPC from remote MCP server."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(
                    server.endpoint_url,  # type: ignore
                    json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                )
                if res.status_code != 200:
                    self._server_health[server.id] = False
                    raise MCPError(f"Remote MCP server returned status {res.status_code}")
                data = res.json()
                tools_data = data.get("result", {}).get("tools", [])
                return [MCPToolDefinition(**t) for t in tools_data]
        except Exception as e:
            self._server_health[server.id] = False
            raise MCPError(f"Failed to discover tools from remote server '{server.id}': {str(e)}")

    async def invoke_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> MCPCallToolResult:
        """Invoke an MCP tool via its server connection."""
        server = self._servers.get(server_id)
        if not server:
            raise MCPError(f"MCP server '{server_id}' is not configured")
        if not self._server_health.get(server_id, False):
            raise MCPError(f"MCP server '{server_id}' is currently unavailable or disconnected")

        if server.transport == "in_memory":
            return await self._invoke_simulated_tool(server_id, tool_name, arguments)
        else:
            return await self._invoke_remote_tool(server, tool_name, arguments)

    async def _invoke_simulated_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> MCPCallToolResult:
        """Execute built-in in-memory MCP tool."""
        if server_id == "enterprise_kb" and tool_name == "query_knowledge_base":
            query = arguments.get("query", "")
            dept = arguments.get("department", "general")
            return MCPCallToolResult(
                content=[
                    MCPTextContent(
                        type="text",
                        text=(
                            f'{{"status": "found", "department": "{dept}", '
                            f'"policy_code": "POL-2026-AI", '
                            f'"summary": "All autonomous agent executions for query \'{query}\' '
                            f'must log execution traces and mandate approval for sensitive operations."}}'
                        ),
                    )
                ],
                isError=False,
            )
        return MCPCallToolResult(
            content=[MCPTextContent(type="text", text=f"Tool {tool_name} not found on server {server_id}")],
            isError=True,
        )

    async def _invoke_remote_tool(
        self,
        server: MCPServerConfig,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> MCPCallToolResult:
        """Call remote MCP tools/call method."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    server.endpoint_url,  # type: ignore
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": tool_name, "arguments": arguments},
                    },
                )
                if res.status_code != 200:
                    raise MCPError(f"Remote MCP invocation error status {res.status_code}")
                data = res.json()
                if "error" in data:
                    return MCPCallToolResult(
                        content=[MCPTextContent(type="text", text=str(data["error"]))],
                        isError=True,
                    )
                result_payload = data.get("result", {})
                return MCPCallToolResult(**result_payload)
        except Exception as e:
            self._server_health[server.id] = False
            raise MCPError(f"Failed to communicate with remote MCP server '{server.id}': {str(e)}")

    async def sync_tools_to_registry(self) -> int:
        """Discover tools from all enabled MCP servers and register them into ToolRegistry."""
        registry = ToolRegistry.get_instance()
        total_synced = 0

        for server_id, server in self._servers.items():
            if not server.enabled:
                continue
            try:
                tools = await self.discover_tools(server_id)
                registered_ids = []
                for tool_def in tools:
                    adapter = MCPToolAdapter(
                        server_id=server_id,
                        tool_def=tool_def,
                        invoker=self.invoke_tool,
                    )
                    registry.register(adapter)
                    registered_ids.append(adapter.id)
                    total_synced += 1
                self._registered_mcp_tools[server_id] = registered_ids
                self._server_health[server_id] = True
            except Exception as e:
                logger.warning(f"Could not sync MCP tools from server '{server_id}': {e}")
                self._server_health[server_id] = False

        return total_synced

