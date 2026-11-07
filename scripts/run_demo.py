"""End-to-End Terminal Demo for AgentFlow AI Multi-Agent Workflow."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import AsyncSessionLocal, init_db
from app.schemas.workflow import WorkflowCreate
from app.services.workflow_service import WorkflowService


async def main() -> None:
    print("=" * 70)
    print("  AGENTFLOW AI — MULTI-AGENT ORCHESTRATION PLATFORM DEMO")
    print("=" * 70)

    print("\n1. Initializing Database and State Machine Engine...")
    await init_db()

    service = WorkflowService()

    user_task = "Research enterprise AI trends and prepare a technical report."
    print(f"\n2. Submitting Complex User Task:\n   \"{user_task}\"")

    async with AsyncSessionLocal() as db:
        print("\n3. Planning Workflow & Decomposing into DAG Subtasks...")
        workflow = await service.create_workflow(
            db=db,
            payload=WorkflowCreate(
                name="Enterprise AI Trends Research Demo",
                description="Live demonstration of AgentFlow multi-agent execution pipeline",
                task=user_task,
                requires_approval=False,
            ),
        )

        print(f"   Workflow Created: ID = {workflow.id}")
        print(f"   Subtasks Planned ({len(workflow.tasks)} stages):")
        for t in workflow.tasks:
            deps_str = f" [depends on: {', '.join(t.dependencies)}]" if t.dependencies else ""
            print(f"     • {t.task_id} -> {t.name} (Assigned to: {t.assigned_agent_id}){deps_str}")

        print("\n4. Executing Multi-Agent Pipeline via LangGraph StateGraph...")
        print("   Coordinating Agents: Planner -> Researcher -> Analyst -> Writer -> Reviewer")

        execution = await service.execute_workflow(
            db=db,
            workflow_id=workflow.id,
        )

        print(f"\n   Execution Finished: Status = {execution.status} (Duration: {execution.duration_seconds}s)")

        # Fetch traces
        traces = await service.get_traces(db, workflow.id)
        print(f"\n5. Execution Traces Recorded ({len(traces)} events):")
        for trace in traces:
            dur = f" ({trace.duration_ms:.1f}ms)" if trace.duration_ms else ""
            print(f"     [{trace.event_type}] {trace.step_name}{dur} - Status: {trace.status}")

        # Display Final Deliverable
        final_out = execution.state_data.get("final_output", {})
        print("\n" + "=" * 70)
        print(f"  FINAL CONSOLIDATED DELIVERABLE: {final_out.get('title', 'Report')}")
        print(f"  Quality Audit Score: {final_out.get('review_score')}/100 | Verdict: {final_out.get('review_verdict')}")
        print("=" * 70)
        print(final_out.get("report_markdown", "No deliverable generated."))
        print("=" * 70)
        print("\nAgentFlow AI demonstration finished successfully.\n")


if __name__ == "__main__":
    asyncio.run(main())

