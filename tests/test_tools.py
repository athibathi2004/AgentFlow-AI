"""Tests for Tool Registry and Core Tools."""

import pytest
from app.core.exceptions import ToolNotFoundError
from app.tools.calculator import CalculatorTool
from app.tools.document_search import DocumentSearchTool
from app.tools.json_extractor import StructuredJsonExtractorTool
from app.tools.registry import ToolRegistry
from app.tools.summarizer import TextSummarizationTool


@pytest.mark.asyncio
async def test_calculator_safe_evaluation():
    calc = CalculatorTool()

    # Basic arithmetic
    r1 = await calc.execute(expression="10 + 25 * 2")
    assert r1.status == "SUCCESS"
    assert r1.result["value"] == 60

    # Functions and powers
    r2 = await calc.execute(expression="sqrt(144) + pow(2, 3)")
    assert r2.status == "SUCCESS"
    assert r2.result["value"] == 20

    # Rounding and float division
    r3 = await calc.execute(expression="round(100 / 3, 2)")
    assert r3.status == "SUCCESS"
    assert r3.result["value"] == 33.33


@pytest.mark.asyncio
async def test_calculator_security_boundaries():
    calc = CalculatorTool()

    # Reject non-whitelisted built-in calls (e.g. eval, open, __import__)
    r1 = await calc.execute(expression="__import__('os').system('dir')")
    assert r1.status == "FAILED"
    assert "not permitted" in r1.error or "whitelist" in r1.error or "Unsupported" in r1.error

    # Reject variables/names
    r2 = await calc.execute(expression="secret_token + 5")
    assert r2.status == "FAILED"

    # Reject division by zero gracefully
    r3 = await calc.execute(expression="10 / 0")
    assert r3.status == "FAILED"
    assert "Division by zero" in r3.error


@pytest.mark.asyncio
async def test_summarizer_tool():
    summarizer = TextSummarizationTool()
    sample_text = (
        "Enterprise artificial intelligence is rapidly transitioning toward autonomous multi-agent pipelines. "
        "These multi-agent architectures leverage LangGraph for state transitions and the Model Context Protocol for tools. "
        "Industry benchmarks indicate a 74% increase in team productivity and an 82% decrease in hallucination rates. "
        "Governance checkpoints ensure that human operators can audit outputs before automated deployment."
    )
    res = await summarizer.execute(text=sample_text, max_bullets=3)
    assert res.status == "SUCCESS"
    assert "executive_summary" in res.result
    assert len(res.result["key_takeaways"]) > 0
    assert res.result["metrics"]["reduction_percentage"] > 0


@pytest.mark.asyncio
async def test_document_search_tool():
    search = DocumentSearchTool()
    res = await search.execute(query="enterprise AI multi-agent LangGraph", max_results=2)
    assert res.status == "SUCCESS"
    assert "documents" in res.result
    assert len(res.result["documents"]) > 0
    top_doc = res.result["documents"][0]
    assert "title" in top_doc
    assert top_doc["relevance_score"] > 0


@pytest.mark.asyncio
async def test_structured_json_extractor_tool():
    extractor = StructuredJsonExtractorTool()

    # Extract JSON inside markdown code fence
    markdown_text = (
        "Here is the synthesized data:\n```json\n"
        '{"status": "ok", "metrics": {"roi": 3.4}, "approved": true}\n'
        "```\nEnd of output."
    )
    res = await extractor.execute(raw_text=markdown_text)
    assert res.status == "SUCCESS"
    assert res.result["extracted_json"]["status"] == "ok"
    assert res.result["extracted_json"]["metrics"]["roi"] == 3.4

    # Extract with target keys filter
    res_filtered = await extractor.execute(raw_text=markdown_text, target_keys=["metrics"])
    assert res_filtered.status == "SUCCESS"
    assert "status" not in res_filtered.result["extracted_json"]
    assert "metrics" in res_filtered.result["extracted_json"]


@pytest.mark.asyncio
async def test_tool_registry_operations():
    registry = ToolRegistry.get_instance()
    tools = registry.list_tools()
    assert len(tools) >= 4

    calc = registry.get("calculator")
    assert calc.id == "calculator"

    # Execution through registry
    exec_res = await registry.execute_tool(
        tool_id="calculator",
        parameters={"expression": "100 - 45"},
    )
    assert exec_res["status"] == "SUCCESS"
    assert exec_res["result"]["value"] == 55

    with pytest.raises(ToolNotFoundError):
        registry.get("invalid_tool_id")

