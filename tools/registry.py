"""Central Tool Registry for discovery, validation, and execution."""

import time
from typing import Any, Dict, List, Optional
from app.core.exceptions import ToolNotFoundError
from app.core.logging import get_logger
from app.tools.base import BaseTool, ToolResult
from app.tools.calculator import CalculatorTool
from app.tools.document_search import DocumentSearchTool
from app.tools.json_extractor import StructuredJsonExtractorTool
from app.tools.summarizer import TextSummarizationTool

logger = get_logger(__name__)


class ToolRegistry:
    """Manages registration, discovery, and execution of tools."""

    _instance: Optional["ToolRegistry"] = None

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}
        self._register_defaults()

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _register_defaults(self) -> None:
        """Register default suite of built-in tools."""
        self.register(CalculatorTool())
        self.register(TextSummarizationTool())
        self.register(DocumentSearchTool())
        self.register(StructuredJsonExtractorTool())

    def register(self, tool: BaseTool) -> None:
        """Register a new tool instance."""
        self._tools[tool.id] = tool
        logger.info(f"Registered tool: {tool.id} ({tool.name})")

    def unregister(self, tool_id: str) -> None:
        """Remove a tool from registry."""
        if tool_id in self._tools:
            del self._tools[tool_id]

    def get(self, tool_id: str) -> BaseTool:
        """Retrieve tool by ID or raise ToolNotFoundError."""
        tool = self._tools.get(tool_id)
        if not tool:
            raise ToolNotFoundError(f"Tool with identifier '{tool_id}' not found in registry")
        return tool

    def exists(self, tool_id: str) -> bool:
        """Check if tool is registered."""
        return tool_id in self._tools

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return list of metadata for all registered tools."""
        return [tool.get_metadata() for tool in self._tools.values()]

    async def execute_tool(
        self,
        tool_id: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute named tool with input validation, timing, and error handling."""
        tool = self.get(tool_id)
        start_time = time.perf_counter()
        result: ToolResult = await tool.execute(**parameters)
        duration = round(time.perf_counter() - start_time, 4)

        return {
            "tool_id": tool_id,
            "status": result.status,
            "result": result.result,
            "duration_seconds": duration,
            "error": result.error,
        }

