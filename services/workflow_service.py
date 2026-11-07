"""Workflow Service: connects API endpoints to database models, planner, and orchestrator."""

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.agents.planner import PlannerAgent
from app.agents.registry import AgentRegistry
from app.approvals.service import ApprovalService
from app.core.exceptions import WorkflowExecutionError, WorkflowNotFoundError
from app.core.logging import get_logger
from app.models.approval import ApprovalRequestModel, ApprovalStatus
from app.models.execution import ExecutionStatus, WorkflowExecutionModel
from app.models.trace import ExecutionTraceModel, TraceEventType
from app.models.workflow import (
    TaskStatus,
    WorkflowModel,
    WorkflowStatus,
    WorkflowTaskModel,
)
from app.orchestration.orchestrator import MultiAgentOrchestrator
from app.orchestration.workflow_planner import WorkflowPlanner
from app.schemas.workflow import WorkflowCreate
from app.tracing.service import ExecutionTraceService

logger = get_logger(__name__)


class WorkflowService:
    """Orchestrates CRUD and execution flows for workflows."""

    def __init__(self) -> None:
        self.registry = AgentRegistry.get_instance()
        planner_agent = self.registry.get("planner-agent")
        self.planner = WorkflowPlanner(
            planner_agent=planner_agent,  # type: ignore
            agent_registry=self.registry,
        )
        self.orchestrator = MultiAgentOrchestrator(agent_registry=self.registry)

    async def create_workflow(
        self,
        db: AsyncSession,
        payload: WorkflowCreate,
    ) -> WorkflowModel:
        """Create a new workflow, generate a validated plan, and persist tasks."""
        workflow_id = str(uuid.uuid4())

        # 1. Generate plan using WorkflowPlanner
        plan_data = await self.planner.create_plan(
            task=payload.task,
            parameters={"requires_approval": payload.requires_approval},
        )

        initial_status = (
            WorkflowStatus.PENDING_APPROVAL.value
            if payload.requires_approval
            else WorkflowStatus.DRAFT.value
        )

        # 2. Persist Workflow record
        workflow = WorkflowModel(
            id=workflow_id,
            name=payload.name,
            description=payload.description,
            original_task=payload.task,
            status=initial_status,
            plan_data=plan_data,
            requires_approval=payload.requires_approval,
        )
        db.add(workflow)

        # 3. Persist individual subtasks
        tasks_list = plan_data.get("tasks", [])
        for idx, t in enumerate(tasks_list):
            task_model = WorkflowTaskModel(
                id=str(uuid.uuid4()),
                workflow_id=workflow_id,
                task_id=t.get("task_id", f"task-{idx+1}"),
                name=t.get("name", f"Subtask {idx+1}"),
                description=t.get("description"),
                assigned_agent_id=t.get("assigned_agent_id"),
                status=TaskStatus.PENDING.value,
                dependencies=t.get("dependencies", []),
                input_data=t.get("input_data", {}),
                output_data={},
                order_index=t.get("order_index", idx),
            )
            db.add(task_model)

        await db.commit()
        await db.refresh(workflow)
        logger.info(f"Created workflow {workflow_id} with {len(tasks_list)} tasks")
        return await self.get_workflow(db, workflow_id)

    async def get_workflow(
        self,
        db: AsyncSession,
        workflow_id: str,
    ) -> WorkflowModel:
        """Fetch workflow by ID with pre-loaded relations."""
        stmt = (
            select(WorkflowModel)
            .options(
                selectinload(WorkflowModel.tasks),
                selectinload(WorkflowModel.executions),
                selectinload(WorkflowModel.approval_requests),
            )
            .where(WorkflowModel.id == workflow_id)
        )
        res = await db.execute(stmt)
        workflow = res.scalar_one_or_none()
        if not workflow:
            raise WorkflowNotFoundError(f"Workflow '{workflow_id}' not found")
        return workflow

    async def list_workflows(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
    ) -> List[WorkflowModel]:
        """List workflows ordered by creation date descending."""
        stmt = (
            select(WorkflowModel)
            .options(selectinload(WorkflowModel.tasks))
            .order_by(desc(WorkflowModel.created_at))
            .offset(skip)
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def execute_workflow(
        self,
        db: AsyncSession,
        workflow_id: str,
        inputs: Optional[Dict[str, Any]] = None,
        force_restart: bool = False,
    ) -> WorkflowExecutionModel:
        """Trigger execution of an existing workflow."""
        return await self.orchestrator.execute_workflow(
            db=db,
            workflow_id=workflow_id,
            inputs=inputs,
            force_restart=force_restart,
        )

    async def approve_workflow(
        self,
        db: AsyncSession,
        workflow_id: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Approve pending workflow plan or paused execution."""
        workflow = await self.get_workflow(db, workflow_id)

        # Find pending approval request
        stmt = select(ApprovalRequestModel).where(
            ApprovalRequestModel.workflow_id == workflow_id,
            ApprovalRequestModel.status == ApprovalStatus.PENDING.value,
        )
        res = await db.execute(stmt)
        approval_req = res.scalar_one_or_none()

        if approval_req:
            await ApprovalService.resolve_request(
                db=db,
                approval_id=approval_req.id,
                approved=True,
                notes=notes,
            )

        workflow.status = WorkflowStatus.APPROVED.value
        await db.commit()

        # Resume execution
        execution = await self.orchestrator.resume_workflow(
            db=db,
            workflow_id=workflow_id,
            notes=notes,
        )
        return {
            "workflow_id": workflow_id,
            "status": "APPROVED",
            "execution_id": execution.id,
            "execution_status": execution.status,
            "notes": notes,
        }

    async def reject_workflow(
        self,
        db: AsyncSession,
        workflow_id: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reject workflow plan and mark workflow rejected."""
        workflow = await self.get_workflow(db, workflow_id)

        # Resolve pending approval request
        stmt = select(ApprovalRequestModel).where(
            ApprovalRequestModel.workflow_id == workflow_id,
            ApprovalRequestModel.status == ApprovalStatus.PENDING.value,
        )
        res = await db.execute(stmt)
        approval_req = res.scalar_one_or_none()

        if approval_req:
            await ApprovalService.resolve_request(
                db=db,
                approval_id=approval_req.id,
                approved=False,
                notes=notes,
            )

        workflow.status = WorkflowStatus.REJECTED.value
        await db.commit()

        # Emit rejection trace
        await ExecutionTraceService.record_trace(
            db=db,
            workflow_id=workflow_id,
            execution_id=workflow_id,
            step_name="human_approval",
            event_type=TraceEventType.APPROVAL_RESPONSE.value,
            details={"decision": "REJECTED", "notes": notes},
            status="WARNING",
        )

        return {
            "workflow_id": workflow_id,
            "status": "REJECTED",
            "notes": notes,
        }

    async def get_traces(
        self,
        db: AsyncSession,
        workflow_id: str,
    ) -> List[ExecutionTraceModel]:
        """Retrieve execution traces for workflow."""
        return await ExecutionTraceService.get_traces_for_workflow(db, workflow_id)

    async def list_executions(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
    ) -> List[WorkflowExecutionModel]:
        """List execution runs."""
        stmt = (
            select(WorkflowExecutionModel)
            .options(
                selectinload(WorkflowExecutionModel.agent_executions),
                selectinload(WorkflowExecutionModel.workflow),
            )
            .order_by(desc(WorkflowExecutionModel.started_at))
            .offset(skip)
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_execution_by_id(
        self,
        db: AsyncSession,
        execution_id: str,
    ) -> WorkflowExecutionModel:
        """Fetch single execution run with its agent executions and tool invocations."""
        stmt = (
            select(WorkflowExecutionModel)
            .options(
                selectinload(WorkflowExecutionModel.agent_executions),
                selectinload(WorkflowExecutionModel.tool_invocations),
                selectinload(WorkflowExecutionModel.workflow),
            )
            .where(WorkflowExecutionModel.id == execution_id)
        )
        res = await db.execute(stmt)
        execution = res.scalar_one_or_none()
        if not execution:
            raise WorkflowNotFoundError(f"Execution run '{execution_id}' not found")
        return execution

