"""Deterministic Mock LLM Provider for offline testing, CI, and zero-dependency runs."""

import asyncio
import json
import re
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel
from app.llm.base import BaseLLMProvider


class DeterministicMockLLMProvider(BaseLLMProvider):
    """Predictable, deterministic mock LLM provider designed for offline testing."""

    def __init__(
        self,
        model_name: str = "mock-mistral",
        latency_ms: int = 20,
        fail_next_calls: int = 0,
    ):
        super().__init__(model_name=model_name)
        self.latency_ms = latency_ms
        self.fail_next_calls = fail_next_calls
        self.invocation_count = 0

    @property
    def provider_name(self) -> str:
        return "mock"

    async def is_available(self) -> bool:
        return True

    async def _simulate_latency(self) -> None:
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000.0)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> str:
        self.invocation_count += 1
        if self.fail_next_calls > 0:
            self.fail_next_calls -= 1
            raise RuntimeError("Simulated transient LLM error for testing resilience")

        await self._simulate_latency()

        # Identify context from system prompt or prompt keywords
        combined = f"{system_prompt or ''} {prompt}".lower()

        if "planner" in combined or "decompose" in combined:
            return json.dumps(self._build_planner_response(prompt))
        elif "research" in combined:
            return (
                "Executive Research Findings:\n"
                "1. Multi-agent orchestration architectures with LangGraph represent 68% of enterprise agent deployments.\n"
                "2. Model Context Protocol (MCP) standardized tool calling across heterogenous LLM backends in Q4 2024.\n"
                "3. Safe tool execution sandboxing and Human-in-the-Loop approval gates reduced deployment risk by 82%."
            )
        elif "analyst" in combined or "analysis" in combined:
            return (
                "Quantitative & Strategic Analysis:\n"
                "- Efficiency metric: Autonomous workflow pipelines reduce human turnaround time by 74%.\n"
                "- Risk evaluation: Primary failure mode is unhandled tool schema mismatches; mitigated by Pydantic v2.\n"
                "- Recommended trajectory: Deploy phased rollouts with mandatory HITL approval on high-impact tools."
            )
        elif "writer" in combined:
            return (
                "# Enterprise AI & Multi-Agent Orchestration Technical Report\n\n"
                "## Executive Summary\n"
                "Autonomous multi-agent systems coordinate specialized agents (Planner, Researcher, Analyst, Writer, Reviewer) "
                "through directed state graphs to solve enterprise workflows with auditable execution traces.\n\n"
                "## Key Architectural Pillars\n"
                "- **Deterministic State Graphs**: Sequential and parallel task dependencies managed via LangGraph.\n"
                "- **Model Context Protocol (MCP)**: Universal tool interfaces for secure cross-system integration.\n"
                "- **Human-in-the-Loop Governance**: Mandatory approval gates for plan changes and sensitive actions.\n\n"
                "## Conclusion\n"
                "AgentFlow AI establishes an extensible benchmark for transparent, production-grade agentic orchestration."
            )
        elif "reviewer" in combined or "review" in combined:
            return (
                "Review Evaluation:\n"
                "- Score: 95/100\n"
                "- Status: APPROVED\n"
                "- Feedback: The report meets all technical criteria, addresses the original task with clarity, "
                "and synthesizes findings into actionable recommendations."
            )
        else:
            return f"Processed completion for task: {prompt[:100]}... [Mock Provider Output]"

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Optional[Type[BaseModel]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        self.invocation_count += 1
        if self.fail_next_calls > 0:
            self.fail_next_calls -= 1
            raise RuntimeError("Simulated transient structured LLM error")

        await self._simulate_latency()

        combined = f"{system_prompt or ''} {prompt}".lower()

        if "planner" in combined or "subtask" in combined or "plan" in combined:
            return self._build_planner_response(prompt)
        elif "research" in combined:
            return {
                "summary": "Synthesized findings on enterprise AI orchestration",
                "key_findings": [
                    "LangGraph enables cyclic and DAG execution models with persistent checkpoints.",
                    "MCP creates standard client-server tool protocols avoiding proprietary lock-in.",
                    "Audit traces and verification loops provide compliance-ready transparency."
                ],
                "sources_consulted": ["enterprise_ai_trends.txt", "cloud_native_patterns.txt"],
                "confidence_score": 0.94,
            }
        elif "analyst" in combined or "analysis" in combined:
            return {
                "quantitative_summary": {
                    "efficiency_gain_pct": 74.0,
                    "risk_reduction_pct": 82.0,
                    "pipeline_steps": 5,
                },
                "key_risks": [
                    "Tool schema validation mismatch",
                    "Unbounded recursion in unconstrained graphs",
                ],
                "mitigations": [
                    "Pydantic v2 strict schemas",
                    "Max retry limits and state graph termination conditions",
                ],
                "verdict": "FEASIBLE_AND_RECOMMENDED",
            }
        elif "writer" in combined:
            return {
                "title": "Enterprise AI & Multi-Agent Orchestration Technical Report",
                "sections": [
                    {"heading": "Executive Summary", "content": "Multi-agent systems provide robust task execution."},
                    {"heading": "Architecture", "content": "Modular agents coordinated via LangGraph state graphs."},
                    {"heading": "Governance", "content": "Human approval checkpoints safeguard critical actions."},
                ],
                "word_count": 480,
                "readiness": "READY_FOR_REVIEW",
            }
        elif "reviewer" in combined or "review" in combined:
            return {
                "score": 95,
                "verdict": "APPROVED",
                "strengths": [
                    "Comprehensive coverage of all subtasks",
                    "Structured presentation and quantitative rigor",
                ],
                "improvements": ["Consider real-time streaming traces in next iteration"],
                "approved_for_delivery": True,
            }
        else:
            return {
                "status": "success",
                "response": f"Mock structured response for: {prompt[:80]}",
                "timestamp": "2026-11-07T10:00:00Z",
            }

    def _build_planner_response(self, prompt: str) -> Dict[str, Any]:
        """Generate structured 5-step workflow plan."""
        return {
            "summary": f"Execution plan for: {prompt[:120]}",
            "tasks": [
                {
                    "task_id": "task-1-plan",
                    "name": "Decompose Task and Strategy",
                    "description": "Establish research parameters and pipeline objectives.",
                    "assigned_agent_id": "planner-agent",
                    "dependencies": [],
                    "order_index": 0,
                    "input_data": {"query": prompt},
                },
                {
                    "task_id": "task-2-research",
                    "name": "Gather Evidence and Data",
                    "description": "Collect industry insights and relevant corpus documentation using search tools.",
                    "assigned_agent_id": "research-agent",
                    "dependencies": ["task-1-plan"],
                    "order_index": 1,
                    "input_data": {"search_terms": ["enterprise AI", "multi-agent orchestration"]},
                },
                {
                    "task_id": "task-3-analysis",
                    "name": "Perform Quantitative Analysis",
                    "description": "Evaluate metrics, trade-offs, and synthesize risks.",
                    "assigned_agent_id": "analysis-agent",
                    "dependencies": ["task-2-research"],
                    "order_index": 2,
                    "input_data": {},
                },
                {
                    "task_id": "task-4-write",
                    "name": "Author Technical Deliverable",
                    "description": "Draft executive report with structured findings and recommendations.",
                    "assigned_agent_id": "writer-agent",
                    "dependencies": ["task-3-analysis"],
                    "order_index": 3,
                    "input_data": {},
                },
                {
                    "task_id": "task-5-review",
                    "name": "Quality Audit and Review",
                    "description": "Evaluate the report against accuracy, completeness, and governance standards.",
                    "assigned_agent_id": "reviewer-agent",
                    "dependencies": ["task-4-write"],
                    "order_index": 4,
                    "input_data": {},
                },
            ],
            "estimated_duration_seconds": 12,
        }

