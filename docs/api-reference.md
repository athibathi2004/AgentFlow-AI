# AgentFlow AI — REST API Reference (v1)

Base URL prefix: `/api/v1`  
Interactive OpenAPI Swagger Docs: `http://localhost:8000/docs`  
ReDoc Documentation: `http://localhost:8000/redoc`

---

## Summary of Implemented Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | System health, database status, LLM availability, tool counts |
| `GET` | `/api/v1/agents` | List all registered specialized agents |
| `GET` | `/api/v1/agents/{agent_id}` | Retrieve agent configuration, system prompt, and schemas |
| `POST` | `/api/v1/workflows` | Deconstruct a task and create an execution plan |
| `GET` | `/api/v1/workflows` | List workflows with pagination (`skip`, `limit`) |
| `GET` | `/api/v1/workflows/{workflow_id}` | Retrieve workflow details, planned tasks, and executions |
| `POST` | `/api/v1/workflows/{workflow_id}/execute` | Trigger LangGraph multi-agent pipeline execution |
| `POST` | `/api/v1/workflows/{workflow_id}/approve` | Approve plan or action, resuming paused workflow |
| `POST` | `/api/v1/workflows/{workflow_id}/reject` | Reject plan with reviewer notes |
| `GET` | `/api/v1/workflows/{workflow_id}/traces` | Retrieve fine-grained audit traces for a workflow |
| `GET` | `/api/v1/tools` | List registered tools (built-in and MCP adapters) |
| `POST` | `/api/v1/tools/{tool_id}/execute` | Execute a tool directly with validated parameters |
| `GET` | `/api/v1/executions` | List historical workflow execution runs |
| `GET` | `/api/v1/executions/{execution_id}` | Retrieve execution details, agent breakdowns, and tool calls |

---

## Endpoint Details & Payloads

### 1. `POST /api/v1/workflows`
Creates a workflow and triggers DAG planning by the Planner Agent.

**Request Payload:**
```json
{
  "name": "Enterprise AI Trends Technical Report",
  "description": "Comprehensive market research and architectural synthesis.",
  "task": "Research enterprise AI trends, analyze agentic orchestration architectures, compute efficiency metrics, and prepare a technical deliverable report with quality review.",
  "requires_approval": false
}
```

**Response (`201 Created`):**
```json
{
  "id": "2cea43e7-8be3-413e-a17f-3e72f3b4f656",
  "name": "Enterprise AI Trends Technical Report",
  "original_task": "Research enterprise AI trends...",
  "status": "DRAFT",
  "requires_approval": false,
  "tasks": [
    {
      "task_id": "task-research",
      "name": "Knowledge & Document Retrieval",
      "assigned_agent_id": "research-agent",
      "status": "PENDING",
      "dependencies": []
    },
    {
      "task_id": "task-analysis",
      "name": "Quantitative & Strategic Analysis",
      "assigned_agent_id": "analysis-agent",
      "status": "PENDING",
      "dependencies": ["task-research"]
    }
  ],
  "created_at": "2026-11-07T10:00:00Z"
}
```

---

### 2. `POST /api/v1/workflows/{workflow_id}/execute`
Runs the multi-agent pipeline via LangGraph.

**Response (`200 OK`):**
```json
{
  "id": "e4b2d56a-1294-4328-98e1-512a87cba122",
  "workflow_id": "2cea43e7-8be3-413e-a17f-3e72f3b4f656",
  "status": "COMPLETED",
  "started_at": "2026-11-07T10:00:01Z",
  "completed_at": "2026-11-07T10:00:03Z",
  "duration_seconds": 2.14,
  "state_data": {
    "final_output": {
      "title": "Technical Report: Enterprise AI Trends",
      "review_score": 95,
      "review_verdict": "APPROVED",
      "report_markdown": "# Technical Report..."
    }
  }
}
```

---

### 3. `POST /api/v1/tools/{tool_id}/execute`
Direct tool invocation sandbox.

**Request Payload:**
```json
{
  "parameters": {
    "expression": "round((100 - 26) * 1.5, 2)"
  }
}
```

**Response (`200 OK`):**
```json
{
  "tool_id": "calculator",
  "status": "SUCCESS",
  "result": {
    "expression": "round((100 - 26) * 1.5, 2)",
    "value": 111,
    "type": "int"
  },
  "duration_seconds": 0.0004,
  "error": null
}
```

