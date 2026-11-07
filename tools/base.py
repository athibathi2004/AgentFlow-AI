"""Base class definition for AgentFlow tools."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Type
from pydantic import BaseModel, ValidationError
from app.core.exceptions import ToolExecutionError


class ToolResult(BaseModel):
    """Standardized output structure from all tool executions."""

    status: str  # "SUCCESS" | "FAILED" | "PENDING_APPROVAL"
    result: Dict[str, Any]
    error: str | None = None


class BaseTool(ABC):
    """Abstract base class for all tools in AgentFlow AI."""

    id: str
    name: str
    description: str
    parameters_schema: Type[BaseModel]
    is_sensitive: bool = False
    requires_approval: bool = False

    def validate_inputs(self, **kwargs: Any) -> BaseModel:
        """Validate input parameters against declared Pydantic schema."""
        try:
            return self.parameters_schema(**kwargs)
        except ValidationError as e:
            raise ToolExecutionError(
                f"Input validation error for tool '{self.id}': {e.errors()}"
            )

    @abstractmethod
    async def run(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute core tool logic."""
        pass

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute tool with input validation and standardized error encapsulation."""
        try:
            validated = self.validate_inputs(**kwargs)
            res = await self.run(**validated.model_dump())
            return ToolResult(status="SUCCESS", result=res)
        except ToolExecutionError as te:
            return ToolResult(status="FAILED", result={}, error=te.message)
        except Exception as e:
            return ToolResult(status="FAILED", result={}, error=str(e))

    def get_metadata(self) -> Dict[str, Any]:
        """Retrieve tool metadata and JSON Schema."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_sensitive": self.is_sensitive,
            "requires_approval": self.requires_approval,
            "schema_json": self.parameters_schema.model_json_schema(),
        }

