"""Tests for Agent Registry and Specialized Agents."""

import pytest
from app.agents.analyst import AnalysisAgent
from app.agents.planner import PlannerAgent
from app.agents.registry import AgentRegistry
from app.agents.researcher import ResearchAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.writer import WriterAgent
from app.core.exceptions import AgentNotFoundError
from app.llm.mock import DeterministicMockLLMProvider


@pytest.mark.asyncio
async def test_agent_registry_lifecycle():
    registry = AgentRegistry.get_instance()
    agents = registry.list_agents()
    assert len(agents) >= 5

    # Check 5 core roles exist
    roles = {a["role"] for a in agents}
    assert {"planner", "researcher", "analyst", "writer", "reviewer"}.issubset(roles)

    # Retrieval
    planner = registry.get("planner-agent")
    assert planner.id == "planner-agent"

    # Enable/Disable
    registry.disable_agent("planner-agent")
    assert not registry.validate_agent_availability("planner-agent")
    registry.enable_agent("planner-agent")
    assert registry.validate_agent_availability("planner-agent")

    # Non-existent agent
    with pytest.raises(AgentNotFoundError):
        registry.get("non-existent-agent-id")


@pytest.mark.asyncio
async def test_planner_agent_execution(mock_llm: DeterministicMockLLMProvider):
    agent = PlannerAgent(llm_provider=mock_llm)
    res = await agent.execute(
        input_data={"task": "Research cloud native microservices architecture."}
    )
    assert res.status == "SUCCESS"
    assert "tasks" in res.output_data
    assert len(res.output_data["tasks"]) >= 3
    assert res.role == "planner"


@pytest.mark.asyncio
async def test_research_agent_execution(mock_llm: DeterministicMockLLMProvider):
    agent = ResearchAgent(llm_provider=mock_llm)
    res = await agent.execute(
        input_data={"query": "enterprise AI multi-agent trends"}
    )
    assert res.status == "SUCCESS"
    assert "findings" in res.output_data
    assert len(res.output_data["findings"]) > 0
    # Research agent should have called document_search tool
    assert any(call["tool_id"] == "document_search" for call in res.tool_calls)


@pytest.mark.asyncio
async def test_analyst_agent_execution(mock_llm: DeterministicMockLLMProvider):
    agent = AnalysisAgent(llm_provider=mock_llm)
    res = await agent.execute(
        input_data={
            "research_summary": "Evaluated 3 architectural studies.",
            "findings": [{"headline": "Efficiency Boost", "detail": "Autonomous agents save time."}],
        }
    )
    assert res.status == "SUCCESS"
    assert "quantitative_metrics" in res.output_data
    assert "strategic_insights" in res.output_data
    # Analyst should have invoked calculator tool
    assert any(call["tool_id"] == "calculator" for call in res.tool_calls)


@pytest.mark.asyncio
async def test_writer_agent_execution(mock_llm: DeterministicMockLLMProvider):
    agent = WriterAgent(llm_provider=mock_llm)
    res = await agent.execute(
        input_data={
            "original_task": "Enterprise AI Report",
            "research_summary": "Strong growth in agent architectures.",
            "analysis_insights": ["74% efficiency gains observed."],
            "metrics": {"efficiency_gain_pct": 74.0},
        }
    )
    assert res.status == "SUCCESS"
    assert "markdown_content" in res.output_data
    assert len(res.output_data["markdown_content"]) > 50
    assert res.output_data["word_count"] > 10


@pytest.mark.asyncio
async def test_reviewer_agent_execution(mock_llm: DeterministicMockLLMProvider):
    agent = ReviewerAgent(llm_provider=mock_llm)
    sample_doc = (
        "# Executive Technical Report\n\n"
        "## Executive Summary\nMulti-agent workflow orchestration with LangGraph.\n\n"
        "## Recommendations\nAdopt human-in-the-loop checkpoints."
    )
    res = await agent.execute(
        input_data={
            "original_task": "Enterprise AI Technical Report",
            "document_content": sample_doc,
        }
    )
    assert res.status == "SUCCESS"
    assert 0 <= res.output_data["score"] <= 100
    assert res.output_data["verdict"] in ["APPROVED", "REVISION_REQUIRED"]
    assert len(res.output_data["audit_findings"]) >= 3


@pytest.mark.asyncio
async def test_agent_input_validation_error():
    agent = PlannerAgent()
    # Task min_length is 5, pass empty or invalid
    res = await agent.execute(input_data={"task": "hi"})
    assert res.status == "FAILED"
    assert "validation" in res.error.lower()

