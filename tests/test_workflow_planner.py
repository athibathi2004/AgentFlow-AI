"""Tests for Workflow Planner, DAG cycle detection, and topological sorting."""

import pytest
from app.agents.planner import PlannerAgent
from app.agents.registry import AgentRegistry
from app.core.exceptions import WorkflowPlanError
from app.orchestration.workflow_planner import WorkflowPlanner


@pytest.fixture
def planner_service():
    registry = AgentRegistry.get_instance()
    planner_agent = registry.get("planner-agent")
    return WorkflowPlanner(planner_agent=planner_agent, agent_registry=registry)  # type: ignore


@pytest.mark.asyncio
async def test_create_valid_plan(planner_service: WorkflowPlanner):
    plan = await planner_service.create_plan(
        task="Conduct enterprise AI evaluation and compile architecture report."
    )
    assert "tasks" in plan
    assert len(plan["tasks"]) >= 3
    assert "execution_stages" in plan
    assert len(plan["execution_stages"]) >= 2


def test_dependency_validation_missing_task(planner_service: WorkflowPlanner):
    invalid_tasks = [
        {
            "task_id": "task-1",
            "name": "Step 1",
            "assigned_agent_id": "planner-agent",
            "dependencies": ["non-existent-task"],
        }
    ]
    with pytest.raises(WorkflowPlanError) as exc:
        planner_service.validate_plan_structure(invalid_tasks)
    assert "non-existent" in str(exc.value)


def test_cycle_detection(planner_service: WorkflowPlanner):
    cyclic_tasks = [
        {
            "task_id": "task-A",
            "name": "Task A",
            "assigned_agent_id": "planner-agent",
            "dependencies": ["task-B"],
        },
        {
            "task_id": "task-B",
            "name": "Task B",
            "assigned_agent_id": "research-agent",
            "dependencies": ["task-A"],
        },
    ]
    with pytest.raises(WorkflowPlanError) as exc:
        planner_service.validate_plan_structure(cyclic_tasks)
    assert "Circular dependency" in str(exc.value)


def test_topological_sorting_and_parallel_stages(planner_service: WorkflowPlanner):
    tasks = [
        {"task_id": "T1", "dependencies": []},
        {"task_id": "T2", "dependencies": ["T1"]},
        {"task_id": "T3", "dependencies": ["T1"]},
        {"task_id": "T4", "dependencies": ["T2", "T3"]},
    ]
    stages = planner_service.compute_execution_order(tasks)

    # Stage 0: T1
    assert stages[0] == ["T1"]
    # Stage 1: T2 and T3 in parallel!
    assert set(stages[1]) == {"T2", "T3"}
    # Stage 2: T4
    assert stages[2] == ["T4"]

