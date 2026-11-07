/**
 * AgentFlow AI — Frontend Dashboard Controller
 * Fully functional Vanilla JavaScript consuming FastAPI /api/v1 REST endpoints.
 */

const API_BASE = '/api/v1';

// Global state
let currentActiveWorkflow = null;
let currentExecutionId = null;
let pollingInterval = null;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupForms();
  fetchAllData();

  // Periodic health check every 15s
  setInterval(fetchHealth, 15000);
});

/* -------------------------------------------------------------
 * NAVIGATION & TABS
 * ------------------------------------------------------------- */
function setupNavigation() {
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;
      switchTab(target);
    });
  });

  document.getElementById('btnRefreshAll').addEventListener('click', () => {
    fetchAllData();
    showToast('Platform data refreshed', 'info');
  });
}

function switchTab(tabId) {
  document.querySelectorAll('.nav-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tabId);
  });
  document.querySelectorAll('.tab-content').forEach(c => {
    c.classList.toggle('active', c.id === `tab-${tabId}`);
  });

  if (tabId === 'history') fetchExecutions();
  if (tabId === 'approvals') fetchPendingApprovals();
  if (tabId === 'agents') fetchAgents();
  if (tabId === 'tools') fetchTools();
}

/* -------------------------------------------------------------
 * API CALLS & DATA FETCHING
 * ------------------------------------------------------------- */
async function fetchAllData() {
  await Promise.allSettled([
    fetchHealth(),
    fetchWorkflows(),
    fetchAgents(),
    fetchTools(),
    fetchPendingApprovals(),
  ]);
}

async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(`Health status ${res.status}`);
    const data = await res.json();

    const dot = document.querySelector('.status-dot');
    const text = document.getElementById('systemHealthText');
    const pill = document.getElementById('providerName');

    if (data.status === 'healthy') {
      dot.className = 'status-dot healthy';
      text.textContent = 'System: Operational';
    } else {
      dot.className = 'status-dot degraded';
      text.textContent = 'System: Degraded';
    }

    if (data.llm_provider) {
      pill.textContent = `${data.llm_provider.type.toUpperCase()}: ${data.llm_provider.model}`;
      document.getElementById('diagLlm').textContent = `${data.llm_provider.type} (${data.llm_provider.model})`;
    }

    if (data.database) {
      document.getElementById('diagDb').textContent = `SQLAlchemy 2.0 (${data.database.engine})`;
    }
    if (data.mcp) {
      document.getElementById('diagMcp').textContent = `MCP (${data.mcp.servers_count} server connected)`;
    }

    if (data.agents) document.getElementById('kpiAgents').textContent = data.agents.total_registered;
    if (data.tools) document.getElementById('kpiTools').textContent = data.tools.total_registered;
  } catch (err) {
    console.error('Health check failed:', err);
    document.querySelector('.status-dot').className = 'status-dot degraded';
    document.getElementById('systemHealthText').textContent = 'System: Offline';
  }
}

async function fetchWorkflows() {
  try {
    const res = await fetch(`${API_BASE}/workflows?limit=20`);
    if (!res.ok) throw new Error('Failed to fetch workflows');
    const workflows = await res.json();

    document.getElementById('kpiWorkflows').textContent = workflows.length;

    // Render Recent Workflows Table in Overview
    const tbody = document.getElementById('recentWorkflowsBody');
    const monitorSelect = document.getElementById('monitorWorkflowSelect');
    monitorSelect.innerHTML = '<option value="">Select a workflow to inspect...</option>';

    if (!workflows.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No workflows created yet. Click "Create Workflow" above.</td></tr>';
      return;
    }

    tbody.innerHTML = workflows.map(wf => `
      <tr>
        <td>
          <strong>${escapeHtml(wf.name)}</strong>
          <div class="text-xs text-muted font-mono">${wf.id.substring(0, 8)}...</div>
        </td>
        <td><span class="badge ${getStatusBadgeClass(wf.status)}">${wf.status}</span></td>
        <td>${wf.tasks ? wf.tasks.length : 0} subtasks</td>
        <td class="text-muted text-sm">${new Date(wf.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
        <td>
          <button class="btn btn-secondary btn-icon" title="Execute Pipeline" onclick="triggerWorkflowExecution('${wf.id}')">
            ⚡
          </button>
          <button class="btn btn-secondary btn-icon" title="View Plan & Traces" onclick="inspectWorkflow('${wf.id}')">
            🔍
          </button>
        </td>
      </tr>
    `).join('');

    // Populate monitor select
    workflows.forEach(wf => {
      const opt = document.createElement('option');
      opt.value = wf.id;
      opt.textContent = `${wf.name} (${wf.status})`;
      monitorSelect.appendChild(opt);
    });

  } catch (err) {
    console.error('Error fetching workflows:', err);
  }
}

async function fetchAgents() {
  try {
    const res = await fetch(`${API_BASE}/agents`);
    if (!res.ok) throw new Error('Failed to fetch agents');
    const agents = await res.json();

    const container = document.getElementById('agentsGridContainer');
    container.innerHTML = agents.map(a => `
      <div class="agent-card">
        <div>
          <div class="agent-header">
            <h3>${escapeHtml(a.name)}</h3>
            <span class="agent-role">${a.role}</span>
          </div>
          <p class="agent-desc">${escapeHtml(a.description)}</p>
          <div class="caps-list">
            ${a.capabilities.map(c => `<span class="cap-tag">${c}</span>`).join('')}
          </div>
        </div>
        <div class="card-actions">
          <button class="btn btn-secondary btn-block text-sm" onclick="showPromptModal('${a.id}')">
            View System Prompt & Schemas
          </button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error fetching agents:', err);
  }
}

async function fetchTools() {
  try {
    const res = await fetch(`${API_BASE}/tools`);
    if (!res.ok) throw new Error('Failed to fetch tools');
    const tools = await res.json();

    const container = document.getElementById('toolsGridContainer');
    const select = document.getElementById('testToolSelect');
    select.innerHTML = '<option value="">Select a tool to test...</option>';

    container.innerHTML = tools.map(t => {
      const isMcp = t.is_mcp ? '<span class="badge badge-info">MCP Tool</span>' : '<span class="badge badge-secondary">Built-in</span>';
      return `
        <div class="tool-card">
          <div>
            <div class="tool-header">
              <h3>${escapeHtml(t.name)}</h3>
              ${isMcp}
            </div>
            <p class="tool-desc">${escapeHtml(t.description)}</p>
            <div class="text-xs text-muted font-mono">ID: ${t.id}</div>
          </div>
          <button class="btn btn-secondary btn-block text-sm" style="margin-top:1rem;" onclick="selectToolForTest('${t.id}')">
            🧪 Test Tool in Sandbox
          </button>
        </div>
      `;
    }).join('');

    tools.forEach(t => {
      const opt = document.createElement('option');
      opt.value = t.id;
      opt.textContent = `${t.name} (${t.id})`;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error('Error fetching tools:', err);
  }
}

async function fetchPendingApprovals() {
  try {
    const res = await fetch(`${API_BASE}/workflows`);
    if (!res.ok) return;
    const workflows = await res.json();

    const pending = workflows.filter(w => w.status === 'PENDING_APPROVAL');
    document.getElementById('kpiApprovals').textContent = pending.length;
    document.getElementById('approvalBadge').textContent = pending.length;

    const tbody = document.getElementById('approvalsTableBody');
    if (!pending.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No pending approvals in queue. All workflows cleared.</td></tr>';
      return;
    }

    tbody.innerHTML = pending.map(w => `
      <tr>
        <td class="font-mono text-xs">${w.id.substring(0, 8)}...</td>
        <td><strong>${escapeHtml(w.name)}</strong></td>
        <td><span class="badge badge-warning">WORKFLOW_PLAN</span></td>
        <td>${escapeHtml(w.original_task.substring(0, 80))}...</td>
        <td class="text-muted text-sm">${new Date(w.created_at).toLocaleTimeString()}</td>
        <td>
          <button class="btn btn-success btn-icon" title="Approve Plan" onclick="resolveApproval('${w.id}', true)">✓ Approve</button>
          <button class="btn btn-danger btn-icon" title="Reject Plan" onclick="resolveApproval('${w.id}', false)">✕ Reject</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Error fetching approvals:', err);
  }
}

async function fetchExecutions() {
  try {
    const res = await fetch(`${API_BASE}/executions?limit=30`);
    if (!res.ok) throw new Error('Failed to fetch executions');
    const executions = await res.json();

    const tbody = document.getElementById('historyTableBody');
    if (!executions.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No executions recorded yet.</td></tr>';
      return;
    }

    tbody.innerHTML = executions.map(ex => `
      <tr>
        <td class="font-mono text-xs"><strong>${ex.id.substring(0, 8)}...</strong></td>
        <td class="font-mono text-xs text-muted">${ex.workflow_id.substring(0, 8)}...</td>
        <td><span class="badge ${getStatusBadgeClass(ex.status)}">${ex.status}</span></td>
        <td class="text-sm">${new Date(ex.started_at).toLocaleString()}</td>
        <td>${ex.duration_seconds ? ex.duration_seconds.toFixed(3) + 's' : '--'}</td>
        <td>
          <button class="btn btn-secondary text-sm" onclick="inspectExecution('${ex.id}', '${ex.workflow_id}')">
            Audit Traces
          </button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Error fetching executions:', err);
  }
}

/* -------------------------------------------------------------
 * WORKFLOW CREATION & EXECUTION
 * ------------------------------------------------------------- */
function setupForms() {
  // Workflow creation form
  const wfForm = document.getElementById('workflowForm');
  wfForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btnCreateWf');
    btn.disabled = true;
    btn.innerHTML = 'Planning with Planner Agent...';

    const payload = {
      name: document.getElementById('wfName').value.trim(),
      description: document.getElementById('wfDescription').value.trim() || null,
      task: document.getElementById('wfTask').value.trim(),
      requires_approval: document.getElementById('wfRequireApproval').checked,
    };

    try {
      const res = await fetch(`${API_BASE}/workflows`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Plan creation failed');
      }

      const created = await res.json();
      showToast(`Workflow plan generated with ${created.tasks.length} subtasks!`, 'success');
      currentActiveWorkflow = created;

      renderPlanPreview(created);
      fetchAllData();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = 'Generate Plan & Create';
    }
  });

  // Tool execution tester form
  const toolForm = document.getElementById('toolTestForm');
  toolForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const toolId = document.getElementById('testToolSelect').value;
    const rawParams = document.getElementById('testToolParams').value.trim();

    if (!toolId) {
      showToast('Please select a tool first', 'error');
      return;
    }

    let parsedParams = {};
    try {
      parsedParams = rawParams ? JSON.parse(rawParams) : {};
    } catch (err) {
      showToast('Invalid JSON in parameters field', 'error');
      return;
    }

    const btn = document.getElementById('btnRunToolTest');
    btn.disabled = true;
    btn.innerHTML = 'Executing...';

    try {
      const res = await fetch(`${API_BASE}/tools/${toolId}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ parameters: parsedParams }),
      });

      const data = await res.json();
      document.getElementById('toolResultBox').style.display = 'block';
      document.getElementById('toolResultJson').textContent = JSON.stringify(data, null, 2);

      if (data.status === 'SUCCESS') {
        showToast(`Tool ${toolId} executed in ${data.duration_seconds}s`, 'success');
      } else {
        showToast(`Tool execution returned error: ${data.error}`, 'error');
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '▶ Run Tool';
    }
  });

  // Monitor workflow select change
  document.getElementById('monitorWorkflowSelect').addEventListener('change', (e) => {
    if (e.target.value) {
      loadMonitorWorkflow(e.target.value);
    }
  });

  document.getElementById('btnRefreshMonitor').addEventListener('click', () => {
    const sel = document.getElementById('monitorWorkflowSelect').value;
    if (sel) loadMonitorWorkflow(sel);
  });
}

function renderPlanPreview(workflow) {
  const container = document.getElementById('planPreviewContainer');
  const badge = document.getElementById('planStatusBadge');
  const actions = document.getElementById('planActions');

  badge.className = `badge ${getStatusBadgeClass(workflow.status)}`;
  badge.textContent = workflow.status;
  actions.style.display = 'flex';

  const tasks = workflow.tasks || [];
  container.innerHTML = `
    <div style="margin-bottom: 1rem;">
      <h4>${escapeHtml(workflow.name)}</h4>
      <p class="text-sm text-muted">${escapeHtml(workflow.original_task)}</p>
    </div>
    <div class="tasks-plan-list">
      ${tasks.map(t => `
        <div class="diagnostic-item" style="margin-bottom: 0.5rem;">
          <div>
            <strong>${escapeHtml(t.name)}</strong>
            <div class="text-xs text-muted">Agent: <span class="badge badge-info">${t.assigned_agent_id}</span></div>
            ${t.dependencies && t.dependencies.length ? `<div class="text-xs text-muted">Depends on: ${t.dependencies.join(', ')}</div>` : ''}
          </div>
          <span class="badge badge-secondary">${t.status}</span>
        </div>
      `).join('')}
    </div>
  `;

  document.getElementById('btnExecutePlan').onclick = () => {
    triggerWorkflowExecution(workflow.id);
  };
}

async function triggerWorkflowExecution(workflowId) {
  showToast('Starting multi-agent execution pipeline...', 'info');
  switchTab('monitor');
  document.getElementById('monitorWorkflowSelect').value = workflowId;

  try {
    const res = await fetch(`${API_BASE}/workflows/${workflowId}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });

    if (!res.ok) throw new Error('Execution launch failed');
    const exec = await res.json();
    currentExecutionId = exec.id;

    showToast(`Execution ${exec.id.substring(0,8)} started!`, 'success');
    loadMonitorWorkflow(workflowId);

    // Start live polling
    startLivePolling(workflowId);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function loadMonitorWorkflow(workflowId) {
  try {
    const [wfRes, tracesRes] = await Promise.all([
      fetch(`${API_BASE}/workflows/${workflowId}`),
      fetch(`${API_BASE}/workflows/${workflowId}/traces`),
    ]);

    if (!wfRes.ok) return;
    const wf = await wfRes.json();
    const traces = tracesRes.ok ? await tracesRes.json() : [];

    // Update Status Badge
    const statusBadge = document.getElementById('monitorExecutionStatus');
    statusBadge.className = `badge ${getStatusBadgeClass(wf.status)}`;
    statusBadge.textContent = wf.status;

    // Update Stepper Stages
    updatePipelineStepper(wf, traces);

    // Update Deliverable
    const deliverableBox = document.getElementById('monitorDeliverable');
    const scorePill = document.getElementById('monitorScorePill');

    const executions = wf.executions || [];
    const latestExec = executions.length ? executions[executions.length - 1] : null;

    if (latestExec && latestExec.state_data && latestExec.state_data.final_output) {
      const finalOut = latestExec.state_data.final_output;
      deliverableBox.innerHTML = renderMarkdown(finalOut.report_markdown || 'Report completed.');

      if (finalOut.review_score !== undefined) {
        scorePill.style.display = 'inline-block';
        document.getElementById('monitorScoreValue').textContent = finalOut.review_score;
      }
    } else if (wf.status === 'RUNNING') {
      deliverableBox.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">⚡</div>
          <h4>Multi-Agent Collaboration in Progress</h4>
          <p class="text-muted">Specialized agents are actively gathering evidence, computing metrics, and drafting deliverable...</p>
        </div>
      `;
    }

    // Update Traces
    document.getElementById('monitorTraceCount').textContent = `${traces.length} events`;
    const tracesList = document.getElementById('monitorTracesList');
    if (!traces.length) {
      tracesList.innerHTML = '<p class="text-muted text-center">No trace events recorded for this workflow.</p>';
    } else {
      tracesList.innerHTML = traces.slice().reverse().map(tr => `
        <div class="trace-item ${tr.status}">
          <span class="trace-type">${tr.event_type}</span>
          <div class="trace-details">
            <strong>${escapeHtml(tr.step_name)}</strong>
            ${tr.duration_ms ? `<span class="trace-time">(${tr.duration_ms.toFixed(1)}ms)</span>` : ''}
            <div class="text-xs text-muted">${new Date(tr.timestamp).toLocaleTimeString()}</div>
          </div>
        </div>
      `).join('');
    }

  } catch (err) {
    console.error('Error loading monitor workflow:', err);
  }
}

function updatePipelineStepper(workflow, traces) {
  const steps = ['planner', 'researcher', 'analyst', 'writer', 'reviewer', 'consolidate'];
  const eventTypes = new Set(traces.map(t => t.event_type));
  const stepNames = new Set(traces.map(t => t.step_name));

  steps.forEach((s, idx) => {
    const el = document.getElementById(`step-${s}`);
    const line = document.getElementById(`line-${idx}`);

    el.classList.remove('active', 'completed');
    if (line) line.classList.remove('active');

    if (workflow.status === 'COMPLETED') {
      el.classList.add('completed');
      if (line) line.classList.add('active');
    } else if (workflow.status === 'RUNNING') {
      if (idx === 0) el.classList.add('completed');
      else if (idx === 1) el.classList.add('active');
    }
  });
}

function startLivePolling(workflowId) {
  if (pollingInterval) clearInterval(pollingInterval);
  let ticks = 0;

  pollingInterval = setInterval(async () => {
    ticks++;
    await loadMonitorWorkflow(workflowId);
    if (ticks > 40) clearInterval(pollingInterval);
  }, 1500);
}

/* -------------------------------------------------------------
 * APPROVALS & DECISIONS
 * ------------------------------------------------------------- */
async function resolveApproval(workflowId, approved) {
  const action = approved ? 'approve' : 'reject';
  const notes = prompt(`Enter optional ${action} notes:`, approved ? 'Approved by operator' : 'Changes requested');

  try {
    const res = await fetch(`${API_BASE}/workflows/${workflowId}/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    });

    if (!res.ok) throw new Error(`Approval resolution failed`);
    showToast(`Workflow ${workflowId.substring(0,8)} ${action}d successfully`, 'success');
    fetchAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

/* -------------------------------------------------------------
 * MODAL INSPECTOR & UTILITIES
 * ------------------------------------------------------------- */
async function inspectWorkflow(workflowId) {
  try {
    const res = await fetch(`${API_BASE}/workflows/${workflowId}`);
    const wf = await res.json();

    document.getElementById('modalTitle').textContent = `Workflow: ${wf.name}`;
    document.getElementById('modalBody').innerHTML = `
      <div style="margin-bottom: 1rem;">
        <span class="badge ${getStatusBadgeClass(wf.status)}">${wf.status}</span>
        <span class="text-xs text-muted font-mono" style="margin-left: 0.5rem;">ID: ${wf.id}</span>
      </div>
      <h4>Task Objective</h4>
      <p class="text-sm text-secondary" style="margin-bottom: 1rem;">${escapeHtml(wf.original_task)}</p>
      <h4>Planned Subtasks</h4>
      <div class="tasks-plan-list">
        ${(wf.tasks || []).map(t => `
          <div class="diagnostic-item" style="margin-bottom: 0.4rem;">
            <div>
              <strong>${escapeHtml(t.name)}</strong>
              <div class="text-xs text-muted">${t.assigned_agent_id || 'unassigned'}</div>
            </div>
            <span class="badge badge-secondary">${t.status}</span>
          </div>
        `).join('')}
      </div>
    `;

    document.getElementById('modalFooter').innerHTML = `
      <button class="btn btn-primary" onclick="triggerWorkflowExecution('${wf.id}'); closeModal();">⚡ Execute Now</button>
      <button class="btn btn-secondary" onclick="closeModal()">Close</button>
    `;

    openModal();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function inspectExecution(executionId, workflowId) {
  try {
    const [execRes, tracesRes] = await Promise.all([
      fetch(`${API_BASE}/executions/${executionId}`),
      fetch(`${API_BASE}/workflows/${workflowId}/traces`),
    ]);

    const exec = await execRes.json();
    const traces = tracesRes.ok ? await tracesRes.json() : [];

    document.getElementById('modalTitle').textContent = `Execution Audit: ${executionId.substring(0,8)}...`;
    document.getElementById('modalBody').innerHTML = `
      <div style="margin-bottom: 1rem;">
        <span class="badge ${getStatusBadgeClass(exec.status)}">${exec.status}</span>
        <span class="text-sm text-muted" style="margin-left: 0.5rem;">Duration: ${exec.duration_seconds ? exec.duration_seconds.toFixed(3) + 's' : '--'}</span>
      </div>
      <h4>Agent Execution Records (${(exec.agent_executions || []).length})</h4>
      <div class="diagnostic-list" style="margin-bottom: 1rem;">
        ${(exec.agent_executions || []).map(ae => `
          <div class="diagnostic-item">
            <div>
              <strong>${ae.agent_id}</strong>
              <div class="text-xs text-muted">${escapeHtml(ae.output_summary || '')}</div>
            </div>
            <span class="badge badge-success">${ae.status}</span>
          </div>
        `).join('')}
      </div>
      <h4>Execution Traces (${traces.length})</h4>
      <div class="traces-timeline" style="max-height: 240px;">
        ${traces.map(t => `
          <div class="trace-item ${t.status}">
            <span class="trace-type">${t.event_type}</span>
            <div class="trace-details">
              <strong>${escapeHtml(t.step_name)}</strong>
              <span class="trace-time">(${t.duration_ms ? t.duration_ms.toFixed(1) + 'ms' : ''})</span>
            </div>
          </div>
        `).join('')}
      </div>
    `;

    openModal();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function showPromptModal(agentId) {
  try {
    const res = await fetch(`${API_BASE}/agents/${agentId}`);
    const a = await res.json();

    document.getElementById('modalTitle').textContent = `${a.name} Specification`;
    document.getElementById('modalBody').innerHTML = `
      <h4>System Prompt</h4>
      <pre class="deliverable-content font-mono" style="min-height:auto; max-height:200px; margin-bottom:1rem;">${escapeHtml(a.system_prompt)}</pre>
      <h4>Capabilities</h4>
      <div class="caps-list" style="margin-bottom:1rem;">
        ${a.capabilities.map(c => `<span class="cap-tag">${c}</span>`).join('')}
      </div>
      <h4>Input Schema</h4>
      <pre class="font-mono text-xs" style="background:var(--bg-surface); padding:0.75rem; border-radius:6px; overflow-x:auto;">${JSON.stringify(a.input_schema, null, 2)}</pre>
    `;

    openModal();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function selectToolForTest(toolId) {
  switchTab('tools');
  const sel = document.getElementById('testToolSelect');
  sel.value = toolId;

  // Prefill realistic sample parameters based on tool ID
  const paramMap = {
    'calculator': '{\n  "expression": "round((100 - 26) * 1.0, 2)"\n}',
    'summarizer': '{\n  "text": "Enterprise multi-agent architectures leverage LangGraph state graphs and MCP tool integrations to decouple reasoning from execution. These systems provide auditable trace trails and approval gates.",\n  "max_bullets": 2\n}',
    'document_search': '{\n  "query": "enterprise AI multi-agent trends",\n  "max_results": 2\n}',
    'json_extractor': '{\n  "raw_text": "Here is the result: ```json {\\"status\\": \\"success\\", \\"score\\": 95} ```",\n  "target_keys": ["score"]\n}',
  };

  document.getElementById('testToolParams').value = paramMap[toolId] || '{\n  \n}';
}

function launchSampleTask() {
  switchTab('studio');
  fillTask('ai-trends');
  document.getElementById('btnCreateWf').click();
}

function fillTask(type) {
  const map = {
    'ai-trends': {
      name: 'Enterprise AI Trends Technical Report',
      desc: 'Research, quantitative analysis, and synthesis of multi-agent architectures.',
      task: 'Research enterprise AI trends, analyze agentic orchestration architectures, compute efficiency metrics, and prepare a technical deliverable report with quality review.',
      approval: false,
    },
    'cloud-security': {
      name: 'Cloud Infrastructure Security Audit',
      desc: 'Evaluate tenant isolation, compute risk indices, and require approval checkpoint.',
      task: 'Audit cloud multi-tenant architecture policies, evaluate isolation mechanisms, quantify compliance gaps, and prepare a security posture review.',
      approval: true,
    },
    'mcp-strategy': {
      name: 'Model Context Protocol (MCP) Evaluation',
      desc: 'Analyze MCP tool interoperability and standardization benefits.',
      task: 'Analyze Model Context Protocol (MCP) tool integration paradigms, calculate glue code reduction impact, and synthesize implementation recommendations.',
      approval: false,
    },
  };

  const item = map[type];
  if (item) {
    document.getElementById('wfName').value = item.name;
    document.getElementById('wfDescription').value = item.desc;
    document.getElementById('wfTask').value = item.task;
    document.getElementById('wfRequireApproval').checked = item.approval;
  }
}

function openModal() {
  document.getElementById('modalOverlay').classList.add('open');
}

function closeModal() {
  document.getElementById('modalOverlay').classList.remove('open');
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function getStatusBadgeClass(status) {
  switch (status) {
    case 'COMPLETED':
    case 'APPROVED':
      return 'badge-success';
    case 'RUNNING':
    case 'PENDING':
      return 'badge-info';
    case 'PENDING_APPROVAL':
    case 'PAUSED':
      return 'badge-warning';
    case 'FAILED':
    case 'REJECTED':
      return 'badge-danger';
    default:
      return 'badge-secondary';
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function renderMarkdown(md) {
  if (!md) return '';
  return md
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    .replace(/^\• (.*$)/gim, '<li>$1</li>')
    .replace(/^\- (.*$)/gim, '<li>$1</li>')
    .replace(/\n\n/gim, '<p></p>')
    .replace(/\n/gim, '<br>');
}

