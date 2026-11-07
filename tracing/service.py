"""Execution Trace Service for recording and retrieving audit trails and metrics."""

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger
from app.models.trace import ExecutionTraceModel, TraceEventType

logger = get_logger(__name__)


class ExecutionTraceService:
    """Service responsible for emitting, persisting, and querying workflow traces."""

    @staticmethod
    async def record_trace(
        db: AsyncSession,
        workflow_id: str,
        execution_id: str,
        step_name: str,
        event_type: str,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "INFO",
    ) -> ExecutionTraceModel:
        """Create and persist an execution trace event."""
        trace = ExecutionTraceModel(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            execution_id=execution_id,
            task_id=task_id,
            agent_id=agent_id,
            step_name=step_name,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            details_json=details or {},
            status=status,
        )
        db.add(trace)
        await db.commit()
        await db.refresh(trace)
        return trace

    @staticmethod
    async def get_traces_for_workflow(
        db: AsyncSession,
        workflow_id: str,
        limit: int = 100,
    ) -> List[ExecutionTraceModel]:
        """Retrieve chronological execution traces for a workflow."""
        stmt = (
            select(ExecutionTraceModel)
            .where(ExecutionTraceModel.workflow_id == workflow_id)
            .order_by(ExecutionTraceModel.timestamp.asc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_traces_for_execution(
        db: AsyncSession,
        execution_id: str,
    ) -> List[ExecutionTraceModel]:
        """Retrieve traces belonging to a specific execution run."""
        stmt = (
            select(ExecutionTraceModel)
            .where(ExecutionTraceModel.execution_id == execution_id)
            .order_by(ExecutionTraceModel.timestamp.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

