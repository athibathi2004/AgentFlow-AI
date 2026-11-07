# Security, Reliability & Guardrail Architecture

## 1. Zero Arbitrary Code Execution Boundary

AgentFlow AI enforces strict security boundaries to prevent malicious or accidental remote code execution:
- **No `eval()` or `exec()`**: The platform contains zero invocations of Python's dynamic code evaluation functions (`eval`, `exec`).
- **Safe Abstract Syntax Tree (AST) Math Evaluator**: The `CalculatorTool` parses mathematical formulas using Python's `ast.parse(mode='eval')` and traverses nodes via an `ast.NodeVisitor` that whitelists only:
  - Binary arithmetic operators (`+`, `-`, `*`, `/`, `//`, `%`, `**`)
  - Unary operators (`-`, `+`)
  - Numerical constants (`int`, `float`, mathematical constants `pi`, `e`)
  - Whitelisted deterministic math functions (`sqrt`, `abs`, `round`, `min`, `max`, `ceil`, `floor`, `log`, `exp`)
- Any AST node representing attributes (`ast.Attribute`), module loading (`ast.Import`), dynamic variables (`ast.Name` not in whitelist), or non-whitelisted function calls is immediately rejected with a `ToolExecutionError`.

---

## 2. Input & Output Contract Validation

- **Pydantic v2 Schemas**: All agent inputs, agent outputs, tool parameters, and REST payloads are validated with strict Pydantic v2 schemas.
- **Fail-Fast Typing**: Malformed inputs or schema drift generate instant validation errors before reaching downstream agents or database models.

---

## 3. Human-in-the-Loop (HITL) Checkpoints

To mitigate rogue autonomous behavior, sensitive operations require human verification:
1. **Plan Approval Gates**: Workflows created with `requires_approval=True` automatically pause after DAG planning. Execution state is persisted as `PAUSED` until an operator issues an approved decision.
2. **Sensitive Tool Approval Flags**: Tools can declare `is_sensitive=True` and `requires_approval=True`.
3. **Persisted Audit Decoupling**: Approvals are tracked in durable database records (`approval_requests`) with reviewer notes, timestamps, and decision outcomes.

---

## 4. Operational Reliability & Resilience

- **Timeout Guards**: All external HTTP/SSE calls to Ollama or remote MCP servers enforce strict timeout limits (default 60s) to prevent thread exhaustion.
- **Exponential Backoff Retries**: Transient failures invoke configurable retries (`MAX_RETRIES=3`, `RETRY_BACKOFF_FACTOR=1.5`).
- **Execution Traces**: Every transition, duration, parameter set, and error is recorded in the `execution_traces` table for auditability and compliance.
- **Secret Hygiene**: Secrets and environment configurations are excluded via `.gitignore`.

