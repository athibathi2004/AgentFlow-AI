"""Tests for Execution Trace Logging and Observability."""

import pytest
from app.db.session import AsyncSessionAdapter
from app.models.trace import TraceEventType
from app.schemas.workflow import WorkflowCreate
from app.services.workflow_service import WorkflowService
from app.tracing.service import ExecutionTraceService


@pytest.mark.asyncio
async def test_trace_creation_and_retrieval(test_db: AsyncSessionAdapter):
    workflow_id = "wf-trace-test"
    execution_id = "exec-trace-test"

    # Emit multiple trace events
    t1 = await ExecutionTraceService.record_trace(
        db=test_db,
        workflow_id=workflow_id,
        execution_id=execution_id,
        step_name="init",
        event_type=TraceEventType.WORKFLOW_START.value,
        details={"info": "started"},
        status="INFO",
    )
    t2 = await ExecutionTraceService.record_trace(
        db=test_db,
        workflow_id=workflow_id,
        execution_id=execution_id,
        step_name="calc_step",
        event_type=TraceEventType.TOOL_CALL.value,
        duration_ms=4.2,
        details={"tool": "calculator"},
        status="SUCCESS",
    )
    t3 = await ExecutionTraceService.record_trace(
        db=test_db,
        workflow_id=workflow_id,
        execution_id=execution_id,
        step_name="finish",
        event_type=TraceEventType.WORKFLOW_END.value,
        duration_ms=12.5,
        status="SUCCESS",
    )

    traces = await ExecutionTraceService.get_traces_for_workflow(test_db, workflow_id)
    assert len(traces) == 3
    assert traces[0].event_type == TraceEventType.WORKFLOW_START.value
    assert traces[1].event_type == TraceEventType.TOOL_CALL.value
    assert traces[1].duration_ms == 4.2
    assert traces[2].event_type == TraceEventType.WORKFLOW_END.value


@pytest.mark.asyncio
async def test_end_to_end_traces_generation(test_db: AsyncSessionAdapter):
    service = WorkflowService()
    wf = await service.create_workflow(
        db=test_db,
        payload=WorkflowCreate(
            name="Traces Verification Workflow",
            task="Research enterprise agent architectures and verify audit logs.",
            requires_approval=False,
        ),
    )
    await service.execute_workflow(db=test_db, workflow_id=wf.id)

    traces = await service.get_traces(test_db, wf.id)
    assert len(traces) >= 5

    event_types = {t.event_type for t in traces}
    assert TraceEventType.WORKFLOW_START.value in event_types
    assert TraceEventType.TOOL_CALL.value in event_types
    assert TraceEventType.AGENT_INVOKE.value in event_types
    assert TraceEventType.WORKFLOW_END.value in event_types

