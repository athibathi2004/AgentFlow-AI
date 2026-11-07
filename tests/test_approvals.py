"""Tests for Human-in-the-Loop Approvals and Checkpoint Resumption."""

import pytest
from app.approvals.service import ApprovalService
from app.db.session import AsyncSessionAdapter
from app.models.approval import ApprovalStatus, ApprovalType
from app.schemas.workflow import WorkflowCreate
from app.services.workflow_service import WorkflowService


@pytest.mark.asyncio
async def test_approval_lifecycle(test_db: AsyncSessionAdapter):
    # Create request
    req = await ApprovalService.create_request(
        db=test_db,
        workflow_id="wf-test-01",
        request_type=ApprovalType.WORKFLOW_PLAN.value,
        details={"plan_summary": "5 subtasks planned"},
    )
    assert req.status == ApprovalStatus.PENDING.value

    # List pending
    pending = await ApprovalService.get_pending_approvals(test_db)
    assert any(p.id == req.id for p in pending)

    # Approve
    resolved = await ApprovalService.resolve_request(
        db=test_db,
        approval_id=req.id,
        approved=True,
        notes="Looks sound to proceed",
    )
    assert resolved.status == ApprovalStatus.APPROVED.value
    assert resolved.reviewer_notes == "Looks sound to proceed"


@pytest.mark.asyncio
async def test_workflow_pause_and_approval_resume(test_db: AsyncSessionAdapter):
    service = WorkflowService()

    # Create workflow requiring approval
    wf = await service.create_workflow(
        db=test_db,
        payload=WorkflowCreate(
            name="Approval Gated Workflow",
            task="Evaluate security posture and require operator signoff.",
            requires_approval=True,
        ),
    )
    assert wf.requires_approval is True

    # Execute -> should pause awaiting approval
    exec_record = await service.execute_workflow(db=test_db, workflow_id=wf.id)
    assert exec_record.status == "PAUSED"

    # Verify pending approval in queue
    pending = await ApprovalService.get_pending_approvals(test_db)
    assert any(p.workflow_id == wf.id for p in pending)

    # Approve workflow -> resumes execution to completion
    approval_res = await service.approve_workflow(
        db=test_db,
        workflow_id=wf.id,
        notes="Operator confirmed clearance",
    )
    assert approval_res["status"] == "APPROVED"
    assert approval_res["execution_status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_workflow_rejection(test_db: AsyncSessionAdapter):
    service = WorkflowService()

    wf = await service.create_workflow(
        db=test_db,
        payload=WorkflowCreate(
            name="Workflow To Reject",
            task="Task that should be rejected by reviewer.",
            requires_approval=True,
        ),
    )
    await service.execute_workflow(db=test_db, workflow_id=wf.id)

    reject_res = await service.reject_workflow(
        db=test_db,
        workflow_id=wf.id,
        notes="Objective does not align with compliance standards",
    )
    assert reject_res["status"] == "REJECTED"

    reloaded_wf = await service.get_workflow(test_db, wf.id)
    assert reloaded_wf.status == "REJECTED"

