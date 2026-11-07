"""Base specialized agent abstraction and execution models."""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field, ValidationError
from app.core.exceptions import AgentExecutionError, ToolExecutionError
from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider
from app.tools.registry import ToolRegistry

logger = get_logger(__name__)


class AgentExecutionResult(BaseModel):
    """Standardized output structure from all agent executions."""

    agent_id: str
    role: str
    status: str  # "SUCCESS" | "FAILED"
    output_data: Dict[str, Any] = Field(default_factory=dict)
    output_summary: str = ""
    duration_seconds: float = 0.0
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class BaseAgent(ABC):
    """Abstract base class for all specialized agents in AgentFlow AI."""

    id: str
    name: str
    role: str
    description: str
    capabilities: List[str]
    system_prompt: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]
    is_enabled: bool = True

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm = llm_provider

    def set_llm_provider(self, provider: BaseLLMProvider) -> None:
        """Assign or switch the LLM provider for this agent."""
        self.llm = provider

    def validate_input(self, data: Dict[str, Any]) -> BaseModel:
        """Validate input payload against the agent's input schema."""
        try:
            return self.input_schema(**data)
        except ValidationError as e:
            raise AgentExecutionError(
                f"Agent '{self.id}' input schema validation failed: {e.errors()}"
            )

    async def call_tool(
        self,
        tool_id: str,
        parameters: Dict[str, Any],
        recorded_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Invoke a tool through ToolRegistry and record invocation metadata."""
        registry = ToolRegistry.get_instance()
        tool = registry.get(tool_id)

        # Check approval requirements
        if tool.requires_approval:
            logger.info(f"Tool {tool_id} flagged as requiring human approval")

        exec_res = await registry.execute_tool(tool_id, parameters)
        record = {
            "tool_id": tool_id,
            "parameters": parameters,
            "status": exec_res["status"],
            "result": exec_res["result"],
            "duration_seconds": exec_res["duration_seconds"],
            "error": exec_res["error"],
        }
        if recorded_calls is not None:
            recorded_calls.append(record)

        if exec_res["status"] != "SUCCESS":
            raise ToolExecutionError(
                f"Tool '{tool_id}' call failed: {exec_res['error']}"
            )
        return exec_res["result"]

    @abstractmethod
    async def process(
        self,
        validated_input: BaseModel,
        context: Dict[str, Any],
        tool_calls: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Core specialized processing logic implemented by child agents."""
        pass

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentExecutionResult:
        """Execute agent with validation, error handling, timing, and observability."""
        if not self.is_enabled:
            return AgentExecutionResult(
                agent_id=self.id,
                role=self.role,
                status="FAILED",
                error=f"Agent '{self.id}' is disabled in the registry",
            )

        start_time = time.perf_counter()
        tool_calls: List[Dict[str, Any]] = []
        ctx = context or {}

        try:
            validated = self.validate_input(input_data)
            output_dict = await self.process(validated, ctx, tool_calls)

            # Validate against output schema
            self.output_schema(**output_dict)

            duration = round(time.perf_counter() - start_time, 4)
            summary = output_dict.get("summary") or output_dict.get("verdict") or str(output_dict)[:160]

            return AgentExecutionResult(
                agent_id=self.id,
                role=self.role,
                status="SUCCESS",
                output_data=output_dict,
                output_summary=str(summary),
                duration_seconds=duration,
                tool_calls=tool_calls,
            )
        except Exception as e:
            duration = round(time.perf_counter() - start_time, 4)
            err_msg = str(e)
            logger.error(f"Error in agent '{self.id}': {err_msg}", exc_info=True)
            return AgentExecutionResult(
                agent_id=self.id,
                role=self.role,
                status="FAILED",
                duration_seconds=duration,
                tool_calls=tool_calls,
                error=err_msg,
            )

    def get_metadata(self) -> Dict[str, Any]:
        """Return agent registration metadata and schemas."""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "capabilities": self.capabilities,
            "is_enabled": self.is_enabled,
            "system_prompt": self.system_prompt,
            "input_schema": self.input_schema.model_json_schema(),
            "output_schema": self.output_schema.model_json_schema(),
        }

