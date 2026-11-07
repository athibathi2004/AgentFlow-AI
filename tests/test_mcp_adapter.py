"""Tests for Model Context Protocol (MCP) Adapter and Manager."""

import pytest
from app.core.exceptions import MCPError
from app.mcp.adapter import MCPToolAdapter
from app.mcp.manager import MCPConnectionManager
from app.mcp.schemas import (
    MCPCallToolResult,
    MCPServerConfig,
    MCPTextContent,
    MCPToolDefinition,
)
from app.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_mcp_tool_adapter_wrapping_and_invocation():
    # Mock invoker
    async def mock_invoker(server_id: str, tool_name: str, arguments: dict):
        return MCPCallToolResult(
            content=[
                MCPTextContent(
                    type="text",
                    text='{"metric": "code_coverage", "value": 98.5}',
                )
            ],
            isError=False,
        )

    tool_def = MCPToolDefinition(
        name="get_coverage_stats",
        description="Query repository code coverage via MCP",
        inputSchema={
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
            },
            "required": ["repo"],
        },
    )

    adapter = MCPToolAdapter(
        server_id="code_mcp",
        tool_def=tool_def,
        invoker=mock_invoker,
    )

    assert adapter.id == "mcp_code_mcp_get_coverage_stats"
    assert adapter.name == "get_coverage_stats (via MCP:code_mcp)"

    # Execution through adapter
    res = await adapter.execute(repo="agentflow-ai")
    assert res.status == "SUCCESS"
    assert res.result["content"]["metric"] == "code_coverage"
    assert res.result["content"]["value"] == 98.5


@pytest.mark.asyncio
async def test_mcp_manager_discovery_and_sync():
    manager = MCPConnectionManager.get_instance()
    servers = await manager.list_servers()
    assert len(servers) >= 1

    # Discover tools from built-in in-memory server
    tools = await manager.discover_tools("enterprise_kb")
    assert len(tools) >= 1
    assert tools[0].name == "query_knowledge_base"

    # Sync to ToolRegistry
    registry = ToolRegistry.get_instance()
    synced_count = await manager.sync_tools_to_registry()
    assert synced_count >= 1
    assert registry.exists("mcp_enterprise_kb_query_knowledge_base")

    # Execution through ToolRegistry
    res = await registry.execute_tool(
        "mcp_enterprise_kb_query_knowledge_base",
        {"query": "data governance policy", "department": "compliance"},
    )
    assert res["status"] == "SUCCESS"
    assert "policy_code" in str(res["result"])


@pytest.mark.asyncio
async def test_mcp_manager_disconnected_server_error():
    manager = MCPConnectionManager.get_instance()
    # Register unavailable server
    manager.register_server(
        MCPServerConfig(
            id="offline_server",
            name="Offline Server",
            transport="sse",
            endpoint_url="http://localhost:99999/mcp",
            enabled=False,
        )
    )

    with pytest.raises(MCPError) as exc:
        await manager.discover_tools("offline_server")
    assert "disabled" in str(exc.value)

    # Clean up
    manager.unregister_server("offline_server")

