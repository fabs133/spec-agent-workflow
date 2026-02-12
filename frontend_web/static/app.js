/* Spec-Agent Workflow System - SPA Frontend */

// ============================================================
// Router
// ============================================================

const routes = {
    'dashboard': renderDashboard,
    'run': renderRunWorkflow,
    'history': renderRunHistory,
    'items': renderItemsBrowser,
    'settings': renderSettings,
    'manifest': renderManifest,
    'arch': renderArchitecture,
    'guide': renderUserGuide,
    'detail': renderRunDetail,
};

let currentPage = '';
let detailRunId = null;

function navigate() {
    const hash = location.hash.replace('#', '') || 'dashboard';
    const parts = hash.split('?');
    const page = parts[0];
    const params = new URLSearchParams(parts[1] || '');

    if (page === 'detail') {
        detailRunId = params.get('run_id');
    }

    currentPage = page;

    // Update sidebar active state
    document.querySelectorAll('.sidebar a').forEach(a => {
        a.classList.toggle('active', a.dataset.page === page);
    });

    const fn = routes[page] || renderDashboard;
    fn();
}

window.addEventListener('hashchange', navigate);
document.addEventListener('DOMContentLoaded', () => {
    navigate();
    updateSidebar();
});

// ============================================================
// API helpers
// ============================================================

async function api(path, opts = {}) {
    const resp = await fetch(path, {
        headers: { 'Content-Type': 'application/json', ...opts.headers },
        ...opts,
    });
    return resp.json();
}

function $(id) { return document.getElementById(id); }
function app() { return $('app'); }

// ============================================================
// Sidebar info
// ============================================================

async function updateSidebar() {
    const settings = await api('/api/settings');
    const hasKey = !!settings.openai_api_key;
    const el = $('sidebar-key-status');
    if (el) {
        el.textContent = hasKey ? 'Set' : 'Not set';
        el.style.color = hasKey ? 'var(--green)' : 'var(--red)';
    }
    const modelEl = $('sidebar-model');
    if (modelEl) modelEl.textContent = settings.default_model || 'gpt-4o';
}

// ============================================================
// Utility renderers
// ============================================================

function statusBadge(status) {
    const cls = { completed: 'pass', passed: 'pass', failed: 'fail', running: 'running', pending: 'pending' };
    return `<span class="badge badge-${cls[status] || 'pending'}">${status}</span>`;
}

function specLine(spec) {
    const icon = spec.passed ? '&#10003;' : '&#10007;';
    const cls = spec.passed ? 'text-green' : 'text-red';
    const name = spec.spec_name || spec.rule_id || '';
    const msg = spec.detail || spec.message || '';
    return `<div class="spec-line"><span class="${cls}">${icon}</span> ${name} - ${msg}</div>`;
}

function renderSpecGroup(title, specs) {
    if (!specs || !specs.length) return `<div><h4>${title}</h4><p class="text-muted text-sm">None</p></div>`;
    const allPassed = specs.every(s => s.passed || s.passed === 1);
    const badge = allPassed
        ? '<span class="badge badge-pass">ALL PASS</span>'
        : '<span class="badge badge-fail">FAILED</span>';
    return `<div><h4>${title} ${badge}</h4>${specs.map(s => specLine(s)).join('')}</div>`;
}

function renderContextDiff(before, after) {
    if (!before || !after) return '';
    const allKeys = new Set([...Object.keys(before), ...Object.keys(after)]);
    let html = '';
    for (const key of [...allKeys].sort()) {
        const bVal = JSON.stringify(before[key], null, 0);
        const aVal = JSON.stringify(after[key], null, 0);
        if (!(key in before)) {
            html += `<div class="diff-added text-sm">+ ${key}: ${trunc(aVal, 120)}</div>`;
        } else if (!(key in after)) {
            html += `<div class="diff-removed text-sm">- ${key}: ${trunc(bVal, 120)}</div>`;
        } else if (bVal !== aVal) {
            html += `<div class="diff-changed text-sm">~ ${key}: ${trunc(bVal, 60)} &rarr; ${trunc(aVal, 60)}</div>`;
        }
    }
    return html || '<p class="text-muted text-sm">No changes</p>';
}

function trunc(s, n) {
    if (!s) return '';
    return s.length > n ? s.slice(0, n) + '...' : s;
}

function duration(start, end) {
    if (!start || !end) return '';
    try {
        const ms = new Date(end) - new Date(start);
        return (ms / 1000).toFixed(1) + 's';
    } catch { return ''; }
}

function mermaidDiagram(stepNames, edges, stepStatuses, currentStep) {
    let lines = ['graph LR'];
    for (const name of stepNames) {
        lines.push(`    ${name}["${name}"]`);
    }
    for (const e of edges) {
        if (e.to === '__end__') continue;
        if (e.condition === 'on_fail') {
            lines.push(`    ${e.from} -.->|fail| ${e.to}`);
        } else {
            lines.push(`    ${e.from} -->|pass| ${e.to}`);
        }
    }
    if (stepStatuses) {
        for (const name of stepNames) {
            const s = stepStatuses[name] || 'pending';
            if (s === 'passed') {
                lines.push(`    style ${name} fill:#d4edda,stroke:#28a745,stroke-width:2px,color:#155724`);
            } else if (s === 'failed') {
                lines.push(`    style ${name} fill:#f8d7da,stroke:#dc3545,stroke-width:2px,color:#721c24`);
            } else if (s === 'running' || name === currentStep) {
                lines.push(`    style ${name} fill:#fff3cd,stroke:#ffc107,stroke-width:2px,color:#856404`);
            } else {
                lines.push(`    style ${name} fill:#e2e3e5,stroke:#6c757d,stroke-width:1px`);
            }
        }
    }
    return lines.join('\n');
}

function renderMermaid(code, id) {
    // Use simple pre-formatted text fallback (no mermaid.js dependency needed)
    return `<div class="mermaid"><pre style="text-align:left;border:none;background:transparent;color:var(--text)">${escHtml(code)}</pre></div>`;
}

function escHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ============================================================
// PAGE: Dashboard
// ============================================================

async function renderDashboard() {
    app().innerHTML = '<p><span class="spinner"></span> Loading dashboard...</p>';

    const [stats, runs, manifest] = await Promise.all([
        api('/api/stats'),
        api('/api/runs?limit=1'),
        api('/api/manifest'),
    ]);

    let html = `
        <h1>Spec-Agent Workflow System</h1>
        <p>A <strong>Spec-Pattern Multi-Agent Architecture</strong> for structured text extraction.
        The system loads text files, extracts structured items via an LLM, and writes the results --
        validating every step with pure specification functions and recording a full execution trace to SQLite.</p>
        <p><a href="#guide">Getting Started -- User Guide</a></p>
        <div class="grid grid-4 mt-1">
            <div class="metric"><span class="label">Total Runs</span><span class="value">${stats.total_runs}</span></div>
            <div class="metric"><span class="label">Completed</span><span class="value text-green">${stats.completed}</span></div>
            <div class="metric"><span class="label">Failed</span><span class="value text-red">${stats.failed}</span></div>
            <div class="metric"><span class="label">Items Extracted</span><span class="value">${stats.total_items}</span></div>
        </div>
        <hr>`;

    if (!runs.length) {
        html += `<div class="alert alert-info">No workflow runs yet. <a href="#run">Start your first run</a>.</div>`;
        app().innerHTML = html;
        return;
    }

    // Last run detail
    const lastRun = runs[0];
    const runData = await api(`/api/runs/${lastRun.id}`);
    const run = runData.run;
    const steps = runData.steps;
    const dur = duration(run.started_at, run.finished_at);

    // Build step info
    const stepMap = {};
    const stepOrder = [];
    for (const step of steps) {
        if (!stepMap[step.step_name]) {
            stepMap[step.step_name] = [];
            stepOrder.push(step.step_name);
        }
        stepMap[step.step_name].push(step);
    }

    const stepFinal = {};
    for (const [name, execs] of Object.entries(stepMap)) {
        if (execs.some(e => e.status === 'passed')) stepFinal[name] = 'passed';
        else if (execs.some(e => e.status === 'failed')) stepFinal[name] = 'failed';
        else stepFinal[name] = execs[execs.length - 1].status;
    }

    const edges = manifest.edges || [];
    const mCode = mermaidDiagram(stepOrder, edges, stepFinal);

    html += `
        <h2>Last Workflow Run</h2>
        <div class="flex flex-wrap flex-center mb-1">
            <span><strong>Status:</strong> ${statusBadge(run.status)}</span>
            <span><strong>Manifest:</strong> <code>${run.manifest_name}</code></span>
            <span><strong>Model:</strong> <code>${run.model_name}</code></span>
            <span><strong>Duration:</strong> ${dur}</span>
        </div>
        <p class="text-xs text-muted">Run ID: <code>${run.id.slice(0, 12)}...</code> | Started: ${(run.started_at || '').slice(0, 19)}</p>

        ${renderMermaid(mCode, 'dashboard-diagram')}

        <p class="text-sm text-muted">Select a step to inspect:</p>
        <div class="flex flex-wrap mb-1" id="step-buttons"></div>
        <div id="step-detail-inline"></div>

        <hr>
        <div class="flex flex-wrap">
            <a href="#run" class="btn btn-primary">Run New Workflow</a>
            <a href="#detail?run_id=${run.id}" class="btn">Full Run Detail</a>
            <a href="#guide" class="btn">User Guide</a>
            <a href="#arch" class="btn">Architecture</a>
        </div>`;

    app().innerHTML = html;

    // Render step buttons
    const btnContainer = $('step-buttons');
    for (const name of stepOrder) {
        const s = stepFinal[name] || 'pending';
        const attempts = stepMap[name].length;
        let label = name;
        if (s === 'passed') label += ' | OK';
        else if (s === 'failed') label += ' | FAIL';
        if (attempts > 1) label += ` (${attempts}x)`;

        const btn = document.createElement('button');
        btn.className = `step-btn ${s}`;
        btn.textContent = label;
        btn.onclick = () => showStepDetail(name, stepMap, stepOrder);
        btnContainer.appendChild(btn);
    }
}

function showStepDetail(selectedStep, stepMap, stepOrder) {
    // Highlight active button
    document.querySelectorAll('.step-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');

    const container = $('step-detail-inline');
    const execs = stepMap[selectedStep];
    if (!execs) { container.innerHTML = ''; return; }

    let html = '<hr>';
    for (const step of execs) {
        const dur = duration(step.started_at, step.finished_at);
        const preSpecs = (step.specs || []).filter(s => s.spec_type === 'pre');
        const postSpecs = (step.specs || []).filter(s => s.spec_type === 'post');
        const invSpecs = (step.specs || []).filter(s => s.spec_type === 'invariant');

        html += `
            <h3>Step: ${selectedStep} -- Attempt ${step.attempt}</h3>
            <p><strong>Status:</strong> ${statusBadge(step.status)} | <strong>Agent:</strong> <code>${step.agent_name}</code> | ${dur}</p>
            ${step.output_summary ? `<div class="alert alert-success">${escHtml(step.output_summary)}</div>` : ''}
            ${step.error_message ? `<div class="alert alert-error">${escHtml(step.error_message)}</div>` : ''}

            <h4>Specification Checks</h4>
            <div class="grid grid-3">
                ${renderSpecGroup('Pre-Specs', preSpecs)}
                ${renderSpecGroup('Post-Specs', postSpecs)}
                ${renderSpecGroup('Invariants', invSpecs)}
            </div>`;

        // Traces
        if (step.traces && step.traces.length) {
            html += '<h4>Agent Actions</h4>';
            for (const t of step.traces) {
                const parts = [`<code>${t.trace_type}</code>`];
                if (t.model_name) parts.push(`model=<code>${t.model_name}</code>`);
                if (t.duration_ms) parts.push(`${t.duration_ms}ms`);
                if (t.tokens_used) parts.push(`${t.tokens_used} tokens`);
                html += `<p class="text-sm">${parts.join(' | ')}</p>`;
                if (t.input_data) {
                    html += `<details><summary>Input</summary><pre>${escHtml(trunc(t.input_data, 2000))}</pre></details>`;
                }
                if (t.output_data) {
                    html += `<details><summary>Output</summary><pre>${escHtml(trunc(t.output_data, 2000))}</pre></details>`;
                }
            }
        }

        // Context diff
        if (step.context_before && step.context_after) {
            html += `<h4>Context Changes</h4>${renderContextDiff(step.context_before, step.context_after)}`;
        }
        html += '<hr>';
    }

    container.innerHTML = html;
}

// ============================================================
// PAGE: Run Workflow
// ============================================================

let _pollInterval = null;

async function renderRunWorkflow() {
    const [settings, manifest, inputFiles] = await Promise.all([
        api('/api/settings'),
        api('/api/manifest'),
        api('/api/input-files'),
    ]);

    const inputFolder = settings.default_input_folder || '';
    const outputFolder = settings.default_output_folder || '';
    const apiKey = settings.openai_api_key || '';
    const model = settings.default_model || 'gpt-4o';

    // Build step order from manifest
    const stepNames = [];
    let cur = manifest.entry_step;
    const visited = new Set();
    while (cur && cur !== '__end__' && !visited.has(cur)) {
        stepNames.push(cur);
        visited.add(cur);
        const edge = manifest.edges.find(e => e.from === cur && e.condition !== 'on_fail');
        cur = edge ? edge.to : null;
    }

    const edges = manifest.edges || [];
    const mCode = mermaidDiagram(stepNames, edges);

    let filesHtml = '';
    if (inputFiles.files && inputFiles.files.length) {
        filesHtml = `<p><strong>Input files found:</strong> ${inputFiles.files.length}</p>
            <ul>${inputFiles.files.map(f => `<li><code>${f.name}</code> (${f.size} bytes)</li>`).join('')}</ul>`;
    } else {
        filesHtml = '<div class="alert alert-warning">No .txt or .md files found in the input folder.</div>';
    }

    app().innerHTML = `
        <h1>Run Workflow</h1>
        <h2>Configuration</h2>
        <div class="grid grid-2">
            <div><label>Input Folder</label><input type="text" id="input-folder" value="${escHtml(inputFolder)}"></div>
            <div><label>Output Folder</label><input type="text" id="output-folder" value="${escHtml(outputFolder)}"></div>
        </div>
        <div class="grid grid-2">
            <div><label>OpenAI API Key</label><input type="password" id="api-key" value="${escHtml(apiKey)}"></div>
            <div><label>Model</label>
                <select id="model-select">
                    ${['gpt-4o', 'gpt-4o-mini', 'gpt-4.1-nano', 'gpt-3.5-turbo'].map(m =>
                        `<option value="${m}" ${m === model ? 'selected' : ''}>${m}</option>`
                    ).join('')}
                </select>
            </div>
        </div>
        <button onclick="saveRunSettings()">Save Settings</button>
        <div id="save-msg" class="mt-1"></div>

        <hr>
        ${filesHtml}
        <hr>

        <h2>Execute Workflow</h2>
        ${renderMermaid(mCode, 'run-diagram')}
        <div id="run-progress"></div>
        <div id="run-status"></div>
        <div id="run-steps"></div>
        <button class="btn-primary mt-1" id="start-btn" onclick="startWorkflow()" ${!apiKey ? 'disabled' : ''}>Start Workflow</button>
        ${!apiKey ? '<p class="text-sm text-orange mt-1">Set an API key to enable workflow execution.</p>' : ''}`;
}

async function saveRunSettings() {
    const body = {
        openai_api_key: $('api-key').value,
        default_model: $('model-select').value,
        default_input_folder: $('input-folder').value,
        default_output_folder: $('output-folder').value,
    };
    await api('/api/settings', { method: 'POST', body: JSON.stringify(body) });
    $('save-msg').innerHTML = '<div class="alert alert-success">Settings saved!</div>';
    updateSidebar();
    setTimeout(() => { if ($('save-msg')) $('save-msg').innerHTML = ''; }, 2000);
}

async function startWorkflow() {
    const btn = $('start-btn');
    btn.disabled = true;
    btn.textContent = 'Starting...';

    const body = {
        api_key: $('api-key').value,
        model: $('model-select').value,
        input_folder: $('input-folder').value,
        output_folder: $('output-folder').value,
    };

    const result = await api('/api/workflow/run', { method: 'POST', body: JSON.stringify(body) });

    if (result.error) {
        $('run-status').innerHTML = `<div class="alert alert-error">${escHtml(result.error)}</div>`;
        btn.disabled = false;
        btn.textContent = 'Start Workflow';
        return;
    }

    $('run-status').innerHTML = '<div class="alert alert-info"><span class="spinner"></span> Workflow running...</div>';

    // Poll for status
    if (_pollInterval) clearInterval(_pollInterval);
    _pollInterval = setInterval(() => pollWorkflow(result.run_id), 1500);
}

async function pollWorkflow(runId) {
    const wf = await api(`/api/workflow/status?run_id=${runId}`);
    if (wf.error === 'Workflow not found') return;

    // Update progress
    const stepNames = wf.step_names || [];
    const statuses = wf.step_statuses || {};
    const done = Object.values(statuses).filter(s => s === 'passed').length;
    const pct = stepNames.length ? (done / stepNames.length * 100) : 0;
    $('run-progress').innerHTML = `
        <div class="progress-bar"><div class="fill" style="width:${pct}%"></div></div>
        <p class="text-sm text-muted">Step ${done}/${stepNames.length}</p>`;

    // Step results
    const results = wf.step_results || [];
    let stepsHtml = '';
    for (const r of results) {
        const color = r.status === 'passed' ? 'green' : 'red';
        const icon = r.status === 'passed' ? 'OK' : 'FAIL';
        stepsHtml += `<p class="text-${color}">${icon} <strong>${r.step_id}</strong> (attempt ${r.attempt})</p>`;
        if (r.error) stepsHtml += `<div class="alert alert-error">${escHtml(r.error)}</div>`;

        for (const spec of [...(r.pre_results||[]), ...(r.post_results||[]), ...(r.invariant_results||[])]) {
            const sIcon = spec.passed ? '&#10003;' : '&#10007;';
            const sCls = spec.passed ? 'text-green' : 'text-red';
            stepsHtml += `<p class="text-sm ${sCls}">&ensp;${sIcon} ${spec.rule_id} - ${spec.message}</p>`;
        }
    }
    $('run-steps').innerHTML = stepsHtml;

    // Done?
    if (wf.status !== 'running') {
        clearInterval(_pollInterval);
        _pollInterval = null;
        $('start-btn').disabled = false;
        $('start-btn').textContent = 'Start Workflow';

        if (wf.status === 'completed') {
            $('run-status').innerHTML = `<div class="alert alert-success">
                Workflow completed! Run ID: <code>${runId.slice(0, 8)}...</code>
                ${wf.items_count ? `<br>Extracted <strong>${wf.items_count}</strong> item(s). <a href="#detail?run_id=${runId}">View details</a> | <a href="#items">Browse items</a>` : ''}
            </div>`;
        } else {
            $('run-status').innerHTML = `<div class="alert alert-error">Workflow failed: ${escHtml(wf.error || 'Unknown error')}</div>`;
        }
    }
}

// ============================================================
// PAGE: Run History
// ============================================================

async function renderRunHistory() {
    app().innerHTML = '<p><span class="spinner"></span> Loading...</p>';
    const runs = await api('/api/runs?limit=100');

    if (!runs.length) {
        app().innerHTML = '<h1>Run History</h1><div class="alert alert-info">No runs yet. <a href="#run">Start a workflow</a>.</div>';
        return;
    }

    let html = '<h1>Run History</h1>';
    for (const run of runs) {
        const dur = duration(run.started_at, run.finished_at);
        const progress = run.total_steps ? `${run.completed_steps || 0}/${run.total_steps}` : '';

        html += `<div class="card">
            <div class="flex flex-between flex-center">
                <div>
                    ${statusBadge(run.status)}
                    <strong>${run.manifest_name}</strong>
                    <span class="text-muted text-sm">${(run.started_at || '').slice(0, 19)}</span>
                </div>
                <div>
                    ${progress ? `<span class="text-sm">Steps: ${progress}</span>` : ''}
                    ${dur ? `<span class="text-sm text-muted"> | ${dur}</span>` : ''}
                    <a href="#detail?run_id=${run.id}" class="btn" style="margin-left:0.5rem">View Details</a>
                </div>
            </div>
            <p class="text-xs text-muted mt-1">
                ID: <code>${run.id.slice(0, 12)}...</code> | Model: <code>${run.model_name || ''}</code>
                ${run.error_message ? ` | Error: ${trunc(run.error_message, 80)}` : ''}
            </p>
        </div>`;
    }

    app().innerHTML = html;
}

// ============================================================
// PAGE: Run Detail
// ============================================================

async function renderRunDetail() {
    if (!detailRunId) {
        app().innerHTML = '<h1>Run Detail</h1><div class="alert alert-warning">No run selected. <a href="#history">Go to History</a>.</div>';
        return;
    }

    app().innerHTML = '<p><span class="spinner"></span> Loading run detail...</p>';
    const data = await api(`/api/runs/${detailRunId}`);

    if (data.error) {
        app().innerHTML = `<h1>Run Detail</h1><div class="alert alert-error">${escHtml(data.error)}</div>`;
        return;
    }

    const run = data.run;
    const steps = data.steps;
    const items = data.items;
    const dur = duration(run.started_at, run.finished_at);

    let html = `
        <h1>Run Detail</h1>
        <div class="grid grid-4">
            <div class="metric"><span class="label">Status</span><span class="value">${statusBadge(run.status)}</span></div>
            <div class="metric"><span class="label">Steps</span><span class="value">${run.completed_steps || 0}/${run.total_steps || 0}</span></div>
            <div class="metric"><span class="label">Items</span><span class="value">${items.length}</span></div>
            <div class="metric"><span class="label">Duration</span><span class="value">${dur}</span></div>
        </div>
        <p class="text-xs text-muted mt-1">
            Run ID: <code>${run.id}</code><br>
            Manifest: <code>${run.manifest_name}</code> | Model: <code>${run.model_name}</code><br>
            Input: <code>${run.input_folder}</code> | Output: <code>${run.output_folder}</code>
        </p>
        ${run.error_message ? `<div class="alert alert-error">${escHtml(run.error_message)}</div>` : ''}
        <hr>
        <h2>Step Execution</h2>`;

    for (const step of steps) {
        const sDur = duration(step.started_at, step.finished_at);
        const preSpecs = (step.specs || []).filter(s => s.spec_type === 'pre');
        const postSpecs = (step.specs || []).filter(s => s.spec_type === 'post');
        const invSpecs = (step.specs || []).filter(s => s.spec_type === 'invariant');

        html += `<details ${step.status === 'failed' ? 'open' : ''}>
            <summary>
                ${statusBadge(step.status)} <strong>${step.step_name}</strong> (attempt ${step.attempt})
                <span class="text-muted text-sm"> | ${step.agent_name} | ${sDur}</span>
            </summary>
            <div>
                ${step.output_summary ? `<div class="alert alert-success">${escHtml(step.output_summary)}</div>` : ''}
                ${step.error_message ? `<div class="alert alert-error">${escHtml(step.error_message)}</div>` : ''}

                <div class="grid grid-3">
                    ${renderSpecGroup('Pre-Specs', preSpecs)}
                    ${renderSpecGroup('Post-Specs', postSpecs)}
                    ${renderSpecGroup('Invariants', invSpecs)}
                </div>`;

        // Traces
        if (step.traces && step.traces.length) {
            html += '<h4>Agent Traces</h4>';
            for (const t of step.traces) {
                const parts = [`<code>${t.trace_type}</code>`];
                if (t.model_name) parts.push(`model=<code>${t.model_name}</code>`);
                if (t.duration_ms) parts.push(`${t.duration_ms}ms`);
                if (t.tokens_used) parts.push(`${t.tokens_used} tokens`);
                html += `<p class="text-sm">${parts.join(' | ')}</p>`;
                if (t.input_data) html += `<details><summary>Input</summary><pre>${escHtml(trunc(t.input_data, 2000))}</pre></details>`;
                if (t.output_data) html += `<details><summary>Output</summary><pre>${escHtml(trunc(t.output_data, 2000))}</pre></details>`;
            }
        }

        // Context diff
        if (step.context_before && step.context_after) {
            html += `<h4>Context Changes</h4>${renderContextDiff(step.context_before, step.context_after)}`;
        }

        html += '</div></details>';
    }

    // Items
    if (items.length) {
        html += `<hr><h2>Extracted Items (${items.length})</h2>`;
        for (const item of items) {
            const tags = (item.tags || []).map(t => `<span class="tag">${escHtml(t)}</span>`).join('');
            const conf = item.confidence != null ? `${(item.confidence * 100).toFixed(0)}%` : '';
            html += `<details>
                <summary>
                    <span class="badge badge-${item.item_type === 'bug' ? 'fail' : 'pass'}">${item.item_type}</span>
                    <strong>${escHtml(item.title)}</strong>
                    <span class="text-muted text-sm">${conf} | ${escHtml(item.source_file || '')}</span>
                </summary>
                <div>
                    <p>${escHtml(item.description || '')}</p>
                    <div>${tags}</div>
                </div>
            </details>`;
        }
    }

    app().innerHTML = html;
}

// ============================================================
// PAGE: Items Browser
// ============================================================

async function renderItemsBrowser() {
    app().innerHTML = '<p><span class="spinner"></span> Loading items...</p>';
    const items = await api('/api/items?limit=500');

    let html = `<h1>Items Browser</h1>
        <p class="text-muted">${items.length} item(s) found</p>`;

    if (!items.length) {
        html += '<div class="alert alert-info">No items yet. Run a workflow to extract items.</div>';
        app().innerHTML = html;
        return;
    }

    // Collect filter options
    const types = [...new Set(items.map(i => i.item_type))].sort();
    const allTags = [...new Set(items.flatMap(i => i.tags || []))].sort();

    html += `<div class="flex flex-wrap flex-center mb-1">
        <div>
            <label>Type</label>
            <select id="filter-type" onchange="filterItems()">
                <option value="">All</option>
                ${types.map(t => `<option value="${t}">${t}</option>`).join('')}
            </select>
        </div>
        <div>
            <label>Min Confidence</label>
            <input type="text" id="filter-conf" placeholder="0.0" style="width:80px" onchange="filterItems()">
        </div>
    </div>
    <div id="items-list"></div>`;

    app().innerHTML = html;

    // Store items for filtering
    window._allItems = items;
    filterItems();
}

function filterItems() {
    const typeFilter = $('filter-type') ? $('filter-type').value : '';
    const confFilter = parseFloat(($('filter-conf') ? $('filter-conf').value : '') || '0');
    const items = (window._allItems || []).filter(i => {
        if (typeFilter && i.item_type !== typeFilter) return false;
        if (i.confidence != null && i.confidence < confFilter) return false;
        return true;
    });

    let html = `<p class="text-sm text-muted mb-1">${items.length} item(s) match filters</p>`;
    for (const item of items) {
        const tags = (item.tags || []).map(t => `<span class="tag">${escHtml(t)}</span>`).join('');
        const conf = item.confidence != null ? `${(item.confidence * 100).toFixed(0)}%` : '';
        html += `<details>
            <summary>
                <span class="badge badge-${item.item_type === 'bug' ? 'fail' : 'pass'}">${item.item_type}</span>
                <strong>${escHtml(item.title)}</strong>
                <span class="text-muted text-sm">${conf} | ${escHtml(item.source_file || '')}</span>
            </summary>
            <div>
                <p>${escHtml(item.description || '')}</p>
                <div>${tags}</div>
                <details class="mt-1"><summary class="text-xs">Raw JSON</summary><pre>${escHtml(JSON.stringify(item, null, 2))}</pre></details>
            </div>
        </details>`;
    }

    $('items-list').innerHTML = html;
}

// ============================================================
// PAGE: Settings
// ============================================================

async function renderSettings() {
    const settings = await api('/api/settings');

    app().innerHTML = `
        <h1>Settings</h1>
        <h2>API Configuration</h2>
        <div class="grid grid-2">
            <div><label>OpenAI API Key</label><input type="password" id="s-api-key" value="${escHtml(settings.openai_api_key || '')}"></div>
            <div><label>Model</label>
                <select id="s-model">
                    ${['gpt-4o', 'gpt-4o-mini', 'gpt-4.1-nano', 'gpt-3.5-turbo'].map(m =>
                        `<option value="${m}" ${m === (settings.default_model || 'gpt-4o') ? 'selected' : ''}>${m}</option>`
                    ).join('')}
                </select>
            </div>
        </div>
        <h2>Default Folders</h2>
        <div class="grid grid-2">
            <div><label>Input Folder</label><input type="text" id="s-input" value="${escHtml(settings.default_input_folder || '')}"></div>
            <div><label>Output Folder</label><input type="text" id="s-output" value="${escHtml(settings.default_output_folder || '')}"></div>
        </div>
        <button class="btn-primary" onclick="saveSettings()">Save Settings</button>
        <div id="settings-msg" class="mt-1"></div>`;
}

async function saveSettings() {
    const body = {
        openai_api_key: $('s-api-key').value,
        default_model: $('s-model').value,
        default_input_folder: $('s-input').value,
        default_output_folder: $('s-output').value,
    };
    await api('/api/settings', { method: 'POST', body: JSON.stringify(body) });
    $('settings-msg').innerHTML = '<div class="alert alert-success">Settings saved!</div>';
    updateSidebar();
}

// ============================================================
// PAGE: Manifest
// ============================================================

async function renderManifest() {
    app().innerHTML = '<p><span class="spinner"></span> Loading...</p>';
    const [manifest, raw, specs] = await Promise.all([
        api('/api/manifest'),
        api('/api/manifest/raw'),
        api('/api/specs'),
    ]);

    const stepNames = Object.keys(manifest.steps || {});
    const edges = manifest.edges || [];
    const mCode = mermaidDiagram(stepNames, edges);

    let html = `
        <h1>Manifest Viewer</h1>
        <div class="grid grid-4">
            <div class="metric"><span class="label">Name</span><span class="value" style="font-size:1.2rem">${manifest.name}</span></div>
            <div class="metric"><span class="label">Version</span><span class="value" style="font-size:1.2rem">${manifest.version}</span></div>
            <div class="metric"><span class="label">Steps</span><span class="value" style="font-size:1.2rem">${stepNames.length}</span></div>
            <div class="metric"><span class="label">Edges</span><span class="value" style="font-size:1.2rem">${edges.length}</span></div>
        </div>
        <p class="text-muted mt-1">${manifest.description || ''}</p>

        <h2>Workflow Graph</h2>
        ${renderMermaid(mCode, 'manifest-diagram')}

        <h2>Step Definitions</h2>`;

    for (const [name, step] of Object.entries(manifest.steps || {})) {
        html += `<details>
            <summary><strong>${name}</strong> &rarr; <code>${step.agent_name}</code></summary>
            <div>
                <p><strong>Pre-specs:</strong> ${(step.pre_specs || []).map(s => `<code>${s}</code>`).join(', ') || 'None'}</p>
                <p><strong>Post-specs:</strong> ${(step.post_specs || []).map(s => `<code>${s}</code>`).join(', ') || 'None'}</p>
                <p><strong>Invariant-specs:</strong> ${(step.invariant_specs || []).map(s => `<code>${s}</code>`).join(', ') || 'None'}</p>
                <p><strong>Retry:</strong> max ${step.retry.max_attempts} attempts, ${step.retry.delay_seconds}s delay</p>
            </div>
        </details>`;
    }

    // Spec registry
    html += '<h2>Spec Registry</h2>';
    for (const [name, spec] of Object.entries(specs)) {
        html += `<details>
            <summary><code>${name}</code> ${spec.doc ? `- ${trunc(spec.doc, 60)}` : ''}</summary>
            <div><pre>${escHtml(spec.source || 'Source not available')}</pre></div>
        </details>`;
    }

    // Defaults and budgets
    html += `<h2>Defaults &amp; Budgets</h2>
        <div class="grid grid-2">
            <div class="card"><h4>Defaults</h4><pre>${escHtml(JSON.stringify(manifest.defaults || {}, null, 2))}</pre></div>
            <div class="card"><h4>Budgets</h4><pre>${escHtml(JSON.stringify(manifest.budgets || {}, null, 2))}</pre></div>
        </div>`;

    // Raw source
    html += `<h2>Raw Manifest Source</h2>
        <pre>${escHtml(raw.content || '')}</pre>`;

    app().innerHTML = html;
}

// ============================================================
// PAGE: Architecture
// ============================================================

async function renderArchitecture() {
    app().innerHTML = `
        <h1>Architecture</h1>
        <p>This system implements the <strong>Specification Pattern</strong> in a multi-agent workflow architecture.
        Every step in the pipeline is validated by pure specification functions before and after execution.</p>

        <h2>System Overview</h2>
        <div class="card">
            <p>The architecture consists of five core layers:</p>
            <ol style="padding-left:1.5rem;line-height:2">
                <li><strong>Manifest</strong> -- JSON-defined workflow graph (steps, edges, specs, budgets)</li>
                <li><strong>Specs</strong> -- Pure validation functions (no IO, deterministic, read-only)</li>
                <li><strong>Agents</strong> -- IO-performing actors (file read, LLM call, file write)</li>
                <li><strong>Orchestrator</strong> -- Execution engine (spec checks, routing, retry, tracing)</li>
                <li><strong>Database</strong> -- SQLite storage (runs, steps, specs, traces, items)</li>
            </ol>
        </div>

        <h2>The Specification Pattern</h2>
        <div class="card">
            <p>Specs are <strong>pure functions</strong> that take a Context and return a SpecResult (pass/fail + message).
            They enforce preconditions, postconditions, and invariants at each workflow step.</p>
            <p>Key properties:</p>
            <ul style="padding-left:1.5rem;line-height:2">
                <li><strong>Pure</strong> -- No side effects, no IO, no external calls</li>
                <li><strong>Deterministic</strong> -- Same input always produces the same output</li>
                <li><strong>Composable</strong> -- Specs can be mixed and matched per step via the manifest</li>
                <li><strong>Self-documenting</strong> -- Each spec returns a human-readable message</li>
            </ul>
            <p>Spec types:</p>
            <ul style="padding-left:1.5rem;line-height:2">
                <li><strong>Pre-specs</strong> -- Check preconditions before agent runs</li>
                <li><strong>Post-specs</strong> -- Verify postconditions after agent runs</li>
                <li><strong>Invariant-specs</strong> -- Global constraints that must always hold</li>
            </ul>
        </div>

        <h2>Context</h2>
        <div class="card">
            <p>The <code>Context</code> is the shared state container passed through all steps. It contains:</p>
            <ul style="padding-left:1.5rem;line-height:2">
                <li><code>data</code> -- Mutable dict (loaded_files, extracted_items, written_files)</li>
                <li><code>config</code> -- Immutable dict (api_key, model, temperature)</li>
                <li><code>trace</code> -- List of agent action records</li>
                <li><code>budgets</code> -- Execution limits (max_retries, max_total_steps)</li>
            </ul>
            <p>The orchestrator snapshots context before and after each step for full traceability.</p>
        </div>

        <h2>Orchestrator Loop</h2>
        <div class="card">
            <p>For each step in the workflow graph:</p>
            <ol style="padding-left:1.5rem;line-height:2">
                <li>Run <strong>pre-specs</strong> (fail early if preconditions unmet)</li>
                <li>Snapshot context (before)</li>
                <li>Execute <strong>agent</strong> (IO allowed)</li>
                <li>Snapshot context (after)</li>
                <li>Run <strong>post-specs</strong> (verify agent did its job)</li>
                <li>Run <strong>invariant-specs</strong> (global constraints)</li>
                <li>Save everything to SQLite</li>
                <li>Use <strong>router</strong> to select next step based on pass/fail</li>
            </ol>
            <p>On failure, the step is retried up to <code>max_attempts</code> times with delay.</p>
        </div>

        <h2>Loop Prevention</h2>
        <div class="card">
            <p>The system detects infinite retry loops via <strong>fingerprinting</strong>:</p>
            <ul style="padding-left:1.5rem;line-height:2">
                <li>Each failed attempt computes a fingerprint from: step name + context data keys + failed spec IDs</li>
                <li>If the same fingerprint appears twice for the same step, a <code>LoopDetectedError</code> is raised</li>
                <li>This prevents agents from failing the same way indefinitely</li>
            </ul>
        </div>

        <h2>Database Schema</h2>
        <div class="card">
            <p>Seven SQLite tables with foreign key constraints:</p>
            <table>
                <tr><th>Table</th><th>Purpose</th></tr>
                <tr><td><code>workflow_runs</code></td><td>Top-level run metadata</td></tr>
                <tr><td><code>step_executions</code></td><td>Individual step attempts</td></tr>
                <tr><td><code>spec_results</code></td><td>Spec check outcomes</td></tr>
                <tr><td><code>context_snapshots</code></td><td>Before/after context state</td></tr>
                <tr><td><code>agent_traces</code></td><td>Agent action logs</td></tr>
                <tr><td><code>extracted_items</code></td><td>Structured items from LLM</td></tr>
                <tr><td><code>app_settings</code></td><td>User configuration</td></tr>
            </table>
        </div>

        <h2>Test Coverage</h2>
        <div class="card">
            <table>
                <tr><th>Test Suite</th><th>Tests</th><th>Focus</th></tr>
                <tr><td>test_specs.py</td><td>29</td><td>Pure specification functions</td></tr>
                <tr><td>test_manifest.py</td><td>23</td><td>Manifest loading + validation + routing</td></tr>
                <tr><td>test_repository.py</td><td>22</td><td>Database CRUD operations</td></tr>
                <tr><td>test_orchestrator.py</td><td>8</td><td>Workflow execution loop</td></tr>
                <tr><td><strong>Total</strong></td><td><strong>82</strong></td><td>100% stdlib, zero external deps</td></tr>
            </table>
        </div>`;
}

// ============================================================
// PAGE: User Guide
// ============================================================

async function renderUserGuide() {
    app().innerHTML = `
        <h1>User Guide</h1>

        <h2>Getting Started</h2>
        <div class="card">
            <ol style="padding-left:1.5rem;line-height:2">
                <li>Run <code>python run.py</code> from the project root</li>
                <li>Open <a href="http://localhost:8501">http://localhost:8501</a> in your browser</li>
                <li>Go to <a href="#settings">Settings</a> and enter your OpenAI API key</li>
                <li>Place <code>.txt</code> or <code>.md</code> files in the <code>data/input/</code> folder</li>
                <li>Go to <a href="#run">Run Workflow</a> and click <strong>Start Workflow</strong></li>
                <li>View results in <a href="#items">Items Browser</a> or <a href="#history">Run History</a></li>
            </ol>
        </div>

        <h2>Workflow Steps</h2>
        <div class="card">
            <table>
                <tr><th>Step</th><th>Agent</th><th>What it does</th></tr>
                <tr><td><strong>intake</strong></td><td>intake_agent</td><td>Reads .txt/.md files from input folder into memory</td></tr>
                <tr><td><strong>extract</strong></td><td>extract_agent</td><td>Sends each file to GPT-4o for structured item extraction</td></tr>
                <tr><td><strong>write</strong></td><td>write_agent</td><td>Writes extracted items as JSON + Markdown to output folder</td></tr>
            </table>
        </div>

        <h2>What Gets Extracted</h2>
        <div class="card">
            <p>The LLM extracts structured items with these fields:</p>
            <table>
                <tr><th>Field</th><th>Description</th></tr>
                <tr><td><code>title</code></td><td>Concise title (max 80 chars)</td></tr>
                <tr><td><code>item_type</code></td><td>One of: task, feature, bug, note, decision</td></tr>
                <tr><td><code>description</code></td><td>Brief description (1-3 sentences)</td></tr>
                <tr><td><code>tags</code></td><td>List of relevant tags (1-5)</td></tr>
                <tr><td><code>confidence</code></td><td>Extraction confidence (0.0 to 1.0)</td></tr>
            </table>
        </div>

        <h2>Project Structure</h2>
        <div class="card">
            <pre>
spec-agent-workflow/
  core/           # Spec-pattern engine
    models.py     # Context, SpecResult, StepAttempt, RunRecord
    specs.py      # Pure specification functions + registry
    agents.py     # BaseAgent ABC + registry
    manifest.py   # JSON manifest loader
    orchestrator.py  # Main execution loop
    router.py     # Edge selection logic
    llm_client.py # Stdlib OpenAI API client
  agents/         # Concrete agent implementations
    intake_agent.py
    extract_agent.py
    write_agent.py
    prompts.py
  db/             # SQLite database layer
    connection.py
    repository.py
    schema.sql
  frontend_web/   # Standalone web UI
    server.py     # HTTP server + JSON API
    static/       # HTML/CSS/JS frontend
  manifests/      # Workflow definitions (JSON)
  tests/          # 82 unit tests
  data/           # Input/output files + database
  run.py          # Entry point: python run.py</pre>
        </div>

        <h2>Key Concepts</h2>
        <div class="card">
            <h3>Specification Pattern</h3>
            <p>Every step is validated by pure functions (specs) that check preconditions and postconditions.
            This ensures agents behave correctly and errors are caught early.</p>

            <h3>Manifest-Driven Workflow</h3>
            <p>The workflow graph is defined in a JSON file, not in code. You can change the workflow
            by editing the manifest without modifying any Python code.</p>

            <h3>Full Traceability</h3>
            <p>Every agent action, spec check, and context change is recorded in SQLite.
            You can inspect exactly what happened at every step of every run.</p>
        </div>

        <h2>Troubleshooting</h2>
        <div class="card">
            <table>
                <tr><th>Problem</th><th>Solution</th></tr>
                <tr><td>API key not working</td><td>Check the key in Settings. Ensure it starts with <code>sk-</code>.</td></tr>
                <tr><td>No input files found</td><td>Place <code>.txt</code> or <code>.md</code> files in <code>data/input/</code></td></tr>
                <tr><td>Workflow fails at extract step</td><td>Check API key and internet connection. The LLM call requires network access.</td></tr>
                <tr><td>Port already in use</td><td>Run <code>python run.py --port 8502</code> to use a different port</td></tr>
            </table>
        </div>`;
}
