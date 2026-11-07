"""Tests for Multi-Agent Orchestrator and LangGraph StateGraph execution."""

import pytest
from app.db.session import AsyncSessionAdapter
from app.models.execution import ExecutionStatus
from app.schemas.workflow import WorkflowCreate
from app.services.workflow_service import WorkflowService


@pytest.mark.asyncio
async def test_full_pipeline_orchestration(test_db: AsyncSessionAdapter):
    service = WorkflowService()

    # 1. Create Workflow
    wf = await service.create_workflow(
        db=test_db,
        payload=WorkflowCreate(
            name="Full Pipeline Orchestration Test",
            task="Research enterprise AI trends, analyze metrics, draft deliverable, and conduct review audit.",
            requires_approval=False,
        ),
    )
    assert wf.id is not None
    assert len(wf.tasks) >= 4

    # 2. Execute
    execution = await service.execute_workflow(
        db=test_db,
        workflow_id=wf.id,
    )
    assert execution.status == ExecutionStatus.COMPLETED.value
    assert execution.duration_seconds is not None
    assert execution.duration_seconds >= 0.0

    # 3. State verification
    state = execution.state_data
    assert "final_output" in state
    assert state["final_output"]["review_score"] >= 80
    assert state["final_output"]["review_verdict"] == "APPROVED"
    assert "report_markdown" in state["final_output"]

    # 4. Agent executions verification
    reloaded_exec = await service.get_execution_by_id(test_db, execution.id)
    assert len(reloaded_exec.agent_executions) >= 3


@pytest.mark.asyncio
async def test_orchestrator_handles_nonexistent_workflow(test_db: AsyncSessionAdapter):
    service = WorkflowService()
    from app.core.exceptions import WorkflowNotFoundError

    with pytest.raises(WorkflowNotFoundError):
        await service.execute_workflow(test_db, "fake-workflow-id-999")

