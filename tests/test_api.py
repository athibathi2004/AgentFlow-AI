"""End-to-End API endpoint integration tests for all 14 routes."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_health_endpoint(async_client: AsyncClient):
    res = await async_client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "database" in data
    assert "llm_provider" in data
    assert "agents" in data
    assert "tools" in data
    assert "mcp" in data


@pytest.mark.asyncio
async def test_api_agents_endpoints(async_client: AsyncClient):
    # List all agents
    res = await async_client.get("/api/v1/agents")
    assert res.status_code == 200
    agents = res.json()
    assert len(agents) >= 5

    # Get single agent
    res_single = await async_client.get("/api/v1/agents/planner-agent")
    assert res_single.status_code == 200
    agent = res_single.json()
    assert agent["id"] == "planner-agent"
    assert "system_prompt" in agent

    # 404 for non-existent agent
    res_404 = await async_client.get("/api/v1/agents/ghost-agent")
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_api_tools_endpoints(async_client: AsyncClient):
    # List tools
    res = await async_client.get("/api/v1/tools")
    assert res.status_code == 200
    tools = res.json()
    assert len(tools) >= 4

    # Execute tool directly
    calc_res = await async_client.post(
        "/api/v1/tools/calculator/execute",
        json={"parameters": {"expression": "25 * 4 + 10"}},
    )
    assert calc_res.status_code == 200
    calc_data = calc_res.json()
    assert calc_data["status"] == "SUCCESS"
    assert calc_data["result"]["value"] == 110

    # 404 on missing tool
    res_404 = await async_client.post(
        "/api/v1/tools/non_existent_tool/execute",
        json={"parameters": {}},
    )
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_api_workflows_lifecycle(async_client: AsyncClient):
    # 1. POST /workflows
    create_payload = {
        "name": "API Automated Workflow Test",
        "description": "Integration testing for workflow endpoints",
        "task": "Research enterprise AI trends and compile a technical report.",
        "requires_approval": False,
    }
    create_res = await async_client.post("/api/v1/workflows", json=create_payload)
    assert create_res.status_code == 201
    wf = create_res.json()
    workflow_id = wf["id"]
    assert wf["name"] == create_payload["name"]
    assert len(wf["tasks"]) >= 3

    # 2. GET /workflows
    list_res = await async_client.get("/api/v1/workflows")
    assert list_res.status_code == 200
    workflows = list_res.json()
    assert any(w["id"] == workflow_id for w in workflows)

    # 3. GET /workflows/{id}
    get_res = await async_client.get(f"/api/v1/workflows/{workflow_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == workflow_id

    # 4. POST /workflows/{id}/execute
    exec_res = await async_client.post(
        f"/api/v1/workflows/{workflow_id}/execute",
        json={"inputs": {}},
    )
    assert exec_res.status_code == 200
    execution = exec_res.json()
    execution_id = execution["id"]
    assert execution["status"] == "COMPLETED"

    # 5. GET /workflows/{id}/traces
    traces_res = await async_client.get(f"/api/v1/workflows/{workflow_id}/traces")
    assert traces_res.status_code == 200
    traces = traces_res.json()
    assert len(traces) >= 5

    # 6. GET /executions
    execs_res = await async_client.get("/api/v1/executions")
    assert execs_res.status_code == 200
    exec_list = execs_res.json()
    assert any(e["id"] == execution_id for e in exec_list)

    # 7. GET /executions/{execution_id}
    single_exec_res = await async_client.get(f"/api/v1/executions/{execution_id}")
    assert single_exec_res.status_code == 200
    assert single_exec_res.json()["id"] == execution_id


@pytest.mark.asyncio
async def test_api_workflow_approval_and_rejection(async_client: AsyncClient):
    # Create workflow requiring approval
    wf_res = await async_client.post(
        "/api/v1/workflows",
        json={
            "name": "Approval Workflow API Test",
            "task": "Security and governance verification task.",
            "requires_approval": True,
        },
    )
    wf_id = wf_res.json()["id"]

    # Trigger execution -> pauses
    await async_client.post(f"/api/v1/workflows/{wf_id}/execute", json={})

    # Approve
    app_res = await async_client.post(
        f"/api/v1/workflows/{wf_id}/approve",
        json={"notes": "Approved via REST API"},
    )
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "APPROVED"

    # Create another workflow to reject
    wf_res2 = await async_client.post(
        "/api/v1/workflows",
        json={
            "name": "Rejection Workflow API Test",
            "task": "Disallowed objective task.",
            "requires_approval": True,
        },
    )
    wf_id2 = wf_res2.json()["id"]

    rej_res = await async_client.post(
        f"/api/v1/workflows/{wf_id2}/reject",
        json={"notes": "Rejected due to policy violation"},
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_api_validation_errors(async_client: AsyncClient):
    # Invalid short name / task
    res = await async_client.post(
        "/api/v1/workflows",
        json={"name": "A", "task": "B"},
    )
    assert res.status_code == 422

