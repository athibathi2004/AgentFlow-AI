"""Planner Agent implementation."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent
from app.llm.base import BaseLLMProvider


class PlannerInput(BaseModel):
    task: str = Field(..., min_length=5, description="High-level user task or objective to decompose")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Execution parameters or constraints")


class SubTaskPlanItem(BaseModel):
    task_id: str
    name: str
    description: str
    assigned_agent_id: str
    dependencies: List[str] = Field(default_factory=list)
    order_index: int = 0
    input_data: Dict[str, Any] = Field(default_factory=dict)


class PlannerOutput(BaseModel):
    summary: str
    strategic_objective: str
    tasks: List[SubTaskPlanItem]
    estimated_duration_seconds: int = 15


class PlannerAgent(BaseAgent):
    """Specialized Agent responsible for task decomposition, dependency planning, and agent assignment."""

    id = "planner-agent"
    name = "Planner Agent"
    role = "planner"
    description = (
        "Deconstructs complex user tasks into ordered subtasks, establishes dependency graphs, "
        "and assigns specialized agents to formulate a valid execution pipeline."
    )
    capabilities = [
        "task_decomposition",
        "dependency_mapping",
        "agent_assignment",
        "execution_strategy",
    ]
    system_prompt = (
        "You are the Planner Agent of AgentFlow AI. Your role is to analyze complex user objectives, "
        "decompose them into granular sequential or parallel subtasks, assign them to suitable agents "
        "(researcher, analyst, writer, reviewer), identify cross-task dependencies, and produce an "
        "executable execution plan."
    )
    input_schema = PlannerInput
    output_schema = PlannerOutput

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        super().__init__(llm_provider=llm_provider)

    async def process(
        self,
        validated_input: BaseModel,
        context: Dict[str, Any],
        tool_calls: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        inp: PlannerInput = validated_input  # type: ignore

        if self.llm:
            prompt = (
                f"Task: {inp.task}\n"
                f"Parameters: {inp.parameters}\n"
                f"Context: {context.get('workflow_id', 'new')}\n\n"
                "Decompose this task into subtasks assigned to: research-agent, analysis-agent, writer-agent, reviewer-agent."
            )
            raw_structured = await self.llm.generate_structured(
                prompt=prompt,
                response_schema=PlannerOutput,
                system_prompt=self.system_prompt,
            )
            if "tasks" in raw_structured and raw_structured["tasks"]:
                # Ensure structure integrity
                tasks_list = [SubTaskPlanItem(**t) if isinstance(t, dict) else t for t in raw_structured["tasks"]]
                return {
                    "summary": raw_structured.get("summary", f"Plan for {inp.task[:60]}"),
                    "strategic_objective": raw_structured.get("strategic_objective", inp.task),
                    "tasks": [t.model_dump() for t in tasks_list],
                    "estimated_duration_seconds": raw_structured.get("estimated_duration_seconds", 15),
                }

        # Deterministic fallback pipeline
        return {
            "summary": f"Structured 4-stage pipeline for: {inp.task[:80]}",
            "strategic_objective": inp.task,
            "tasks": [
                {
                    "task_id": "task-research",
                    "name": "Knowledge & Document Retrieval",
                    "description": "Gather empirical data, citations, and market insights relevant to task.",
                    "assigned_agent_id": "research-agent",
                    "dependencies": [],
                    "order_index": 0,
                    "input_data": {"query": inp.task},
                },
                {
                    "task_id": "task-analysis",
                    "name": "Quantitative & Strategic Analysis",
                    "description": "Evaluate findings, calculate metrics, and analyze risks and trade-offs.",
                    "assigned_agent_id": "analysis-agent",
                    "dependencies": ["task-research"],
                    "order_index": 1,
                    "input_data": {},
                },
                {
                    "task_id": "task-write",
                    "name": "Report Drafting & Synthesis",
                    "description": "Author structured deliverable document incorporating research and analysis.",
                    "assigned_agent_id": "writer-agent",
                    "dependencies": ["task-analysis"],
                    "order_index": 2,
                    "input_data": {},
                },
                {
                    "task_id": "task-review",
                    "name": "Quality Audit & Verification",
                    "description": "Evaluate accuracy, completeness, and adherence to user objectives.",
                    "assigned_agent_id": "reviewer-agent",
                    "dependencies": ["task-write"],
                    "order_index": 3,
                    "input_data": {},
                },
            ],
            "estimated_duration_seconds": 15,
        }

