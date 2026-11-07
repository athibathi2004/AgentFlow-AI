"""Seed database with default agents, tools, and sample workflows."""

import asyncio
import json
import os
import sys

# Ensure app package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agents.registry import AgentRegistry
from app.db.session import AsyncSessionLocal, init_db
from app.models.agent import AgentModel
from app.models.tool import ToolModel
from app.schemas.workflow import WorkflowCreate
from app.services.workflow_service import WorkflowService
from app.tools.registry import ToolRegistry


async def seed() -> None:
    print("Initializing database...")
    await init_db()

    async with AsyncSessionLocal() as db:
        print("Seeding registered agents...")
        agent_reg = AgentRegistry.get_instance()
        for agent_meta in agent_reg.list_agents():
            agent_model = AgentModel(
                id=agent_meta["id"],
                name=agent_meta["name"],
                role=agent_meta["role"],
                description=agent_meta["description"],
                capabilities=agent_meta["capabilities"],
                is_enabled=agent_meta["is_enabled"],
                system_prompt=agent_meta["system_prompt"],
                config_json={},
            )
            await db.merge(agent_model)

        print("Seeding registered tools...")
        tool_reg = ToolRegistry.get_instance()
        for tool_meta in tool_reg.list_tools():
            tool_model = ToolModel(
                id=tool_meta["id"],
                name=tool_meta["name"],
                description=tool_meta["description"],
                schema_json=tool_meta["schema_json"],
                is_sensitive=tool_meta["is_sensitive"],
                requires_approval=tool_meta["requires_approval"],
                is_enabled=True,
                is_mcp=tool_meta.get("is_mcp", False),
            )
            await db.merge(tool_model)

        await db.commit()

        # Seed sample workflows
        sample_file = os.path.join(
            os.path.dirname(__file__), "..", "sample-data", "sample_workflows.json"
        )
        if os.path.exists(sample_file):
            print("Seeding sample workflows...")
            with open(sample_file, "r", encoding="utf-8") as f:
                samples = json.load(f)

            workflow_service = WorkflowService()
            for sample in samples:
                payload = WorkflowCreate(**sample)
                wf = await workflow_service.create_workflow(db, payload)
                print(f"Created sample workflow: '{wf.name}' (ID: {wf.id})")

    print("Database seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed())

