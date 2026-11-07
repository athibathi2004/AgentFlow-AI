# AgentFlow AI — System Architecture

## 1. Executive Architecture Overview

**AgentFlow AI** is a modular platform for designing, orchestrating, executing, and monitoring collaborative AI agent workflows. It translates complex, unstructured objectives into discrete subtasks coordinated via directed state graphs, standardizes tool invocations using the Model Context Protocol (MCP), and enforces enterprise governance through Human-in-the-Loop (HITL) checkpoints.

```mermaid
flowchart TD
    subgraph Client["Client Tier"]
        UI["Web Dashboard (Vanilla JS / CSS3)"]
        API_Client["REST API Clients / SDKs"]
    end

    subgraph Gateway["API Gateway Tier"]
        FastAPI["FastAPI 0.110+ Application"]
        CORS["CORS Middleware"]
        AuthZ["Validation & Error Handling"]
    end

    subgraph Core["Core Orchestration & Multi-Agent Engine"]
        PlannerService["Workflow Planner (DAG & Topological Sort)"]
        Orchestrator["Multi-Agent Orchestrator"]
        StateGraph["LangGraph StateGraph Machine"]
        ApprovalService["Human-in-the-Loop Approval Service"]
        TraceService["Execution Trace & Audit Service"]
    end

    subgraph Agents["Specialized Agents Tier"]
        A_Plan["Planner Agent"]
        A_Res["Research Agent"]
        A_Ana["Analysis Agent"]
        A_Wri["Writer Agent"]
        A_Rev["Reviewer Agent"]
    end

    subgraph Tools["Tool Integration Tier"]
        ToolReg["Central Tool Registry"]
        T_Calc["Safe Calculator (AST)"]
        T_Sum["Text Summarizer"]
        T_Doc["Document Search"]
        T_JSON["JSON Extractor"]
        MCP_Adapt["MCP Tool Adapter Layer"]
    end

    subgraph LLM["Provider Abstraction Layer"]
        LLM_Factory["Provider Factory"]
        Ollama["Ollama Local Provider (Mistral / Llama 3)"]
        MockLLM["Deterministic Mock Provider"]
    end

    subgraph Storage["Persistence Tier"]
        SQLAlchemy["SQLAlchemy 2.0 ORM"]
        DB[("PostgreSQL / SQLite Storage")]
    end

    Client --> Gateway
    Gateway --> Core
    Core --> Agents
    Agents --> Tools
    Agents --> LLM
    Tools --> Storage
    Core --> Storage
```

---

## 2. Component Breakdown

### A. Client Tier
- **Frontend Dashboard**: Responsive single-page interface implemented with semantic HTML5, modern CSS3, and vanilla JavaScript using the native Fetch API.
- **REST Consumers**: OpenAPI-compliant client applications consuming versioned JSON endpoints under `/api/v1`.

### B. Gateway Tier
- **FastAPI Core**: Handles request routing, parameter validation using Pydantic v2 schemas, lifespan database setup, and structured JSON error responses.

### C. Orchestration Tier
- **Workflow Planner**: Analyzes user tasks, performs Directed Acyclic Graph (DAG) cycle detection, and computes topological execution orders.
- **LangGraph StateGraph**: Maintains a shared immutable state across pipeline steps (`WorkflowState`), routing transitions conditionally based on approval flags and audit scores.
- **Multi-Agent Orchestrator**: Coordinates node transitions, handles transient retries with configurable limits, and persists execution metadata.

### D. Specialized Agents Tier
Five dedicated autonomous agent implementations with isolated system prompts, schemas, and execution boundaries:
1. `PlannerAgent`: Decomposes tasks into structured subtasks.
2. `ResearchAgent`: Gathers factual evidence and citations via document search tools.
3. `AnalysisAgent`: Computes quantitative metrics and evaluates risks using AST calculators.
4. `WriterAgent`: Synthesizes findings into comprehensive technical deliverables.
5. `ReviewerAgent`: Audits deliverables against requirements, assigning quality scores (0-100).

### E. Tool & MCP Integration Tier
- **Tool Registry**: Manages discovery, schema validation, and execution for native and external tools.
- **MCP Client Adapter**: Implements JSON-RPC 2.0 communication to discover remote tools from MCP servers and map them into the platform's unified tool calling interface.

### F. Persistence Tier
- **SQLAlchemy 2.0**: Relational persistence supporting PostgreSQL in production and SQLite for local development and offline testing.
- **Audit Models**: Workflows, Subtasks, Executions, Agent Executions, Tool Invocations, Approval Requests, and Fine-Grained Execution Traces.

