"""Model Context Protocol (MCP) Tool Adapter.

Wraps external MCP tools into native AgentFlow BaseTool instances.
Note: Supported MCP Integration Level: MCP JSON-RPC 2.0 Client Adapter Layer
(Tool Discovery and Tool Invocations).
"""

import json
from typing import Any, Callable, Coroutine, Dict, Type
from pydantic import BaseModel, create_model
from app.core.exceptions import MCPError, ToolExecutionError
from app.mcp.schemas import MCPCallToolResult, MCPToolDefinition
from app.tools.base import BaseTool


class DynamicMCPInput(BaseModel):
    """Fallback permissive input model for dynamically registered MCP tools."""

    model_config = {"extra": "allow"}


class MCPToolAdapter(BaseTool):
    """Adapter bridging MCP JSON-RPC 2.0 tool interface with AgentFlow BaseTool."""

    def __init__(
        self,
        server_id: str,
        tool_def: MCPToolDefinition,
        invoker: Callable[[str, str, Dict[str, Any]], Coroutine[Any, Any, MCPCallToolResult]],
        is_sensitive: bool = False,
        requires_approval: bool = False,
    ):
        self.server_id = server_id
        self.mcp_name = tool_def.name
        self.id = f"mcp_{server_id}_{tool_def.name}"
        self.name = f"{tool_def.name} (via MCP:{server_id})"
        self.description = tool_def.description or f"MCP-provided tool from {server_id}"
        self.is_sensitive = is_sensitive
        self.requires_approval = requires_approval
        self._invoker = invoker
        self.parameters_schema = self._build_pydantic_schema(tool_def.inputSchema)

    def _build_pydantic_schema(self, schema_dict: Dict[str, Any]) -> Type[BaseModel]:
        """Construct a dynamic Pydantic model from JSON Schema if valid, or fallback."""
        try:
            properties = schema_dict.get("properties", {})
            required_fields = set(schema_dict.get("required", []))
            fields: Dict[str, Any] = {}

            type_mapping = {
                "string": (str, ...),
                "integer": (int, ...),
                "number": (float, ...),
                "boolean": (bool, ...),
                "array": (list, ...),
                "object": (dict, ...),
            }

            for field_name, field_info in properties.items():
                f_type = field_info.get("type", "string")
                py_type, default_val = type_mapping.get(f_type, (Any, ...))
                if field_name not in required_fields:
                    default_val = None
                    py_type = py_type | None
                fields[field_name] = (py_type, default_val)

            if fields:
                return create_model(f"MCP_{self.mcp_name}_Input", **fields)
        except Exception:
            pass
        return DynamicMCPInput

    async def run(self, **kwargs: Any) -> Dict[str, Any]:
        """Invoke remote MCP server method tools/call."""
        try:
            result: MCPCallToolResult = await self._invoker(
                self.server_id,
                self.mcp_name,
                kwargs,
            )
            if result.isError:
                err_text = "Unknown error"
                if result.content:
                    c = result.content[0]
                    err_text = c.text if hasattr(c, "text") else str(c)
                raise ToolExecutionError(f"MCP server execution error: {err_text}")

            # Parse content
            content_list = []
            for item in result.content:
                if hasattr(item, "text"):
                    text_val = item.text
                    try:
                        parsed_json = json.loads(text_val)
                        content_list.append(parsed_json)
                    except Exception:
                        content_list.append(text_val)
                elif isinstance(item, dict):
                    content_list.append(item)
                else:
                    content_list.append(str(item))

            return {
                "server_id": self.server_id,
                "tool_name": self.mcp_name,
                "content": content_list[0] if len(content_list) == 1 else content_list,
            }
        except MCPError as me:
            raise ToolExecutionError(f"MCP protocol failure: {me.message}")
        except Exception as e:
            if isinstance(e, ToolExecutionError):
                raise
            raise ToolExecutionError(f"Failed to execute MCP tool: {str(e)}")

