"""Main Streamlit app entry point -- Dashboard.

Landing page showing:
- Short introduction to the system
- Quick stats (total runs, items extracted)
- Last executed workflow as a flow diagram with clickable step buttons
- Inline step detail: specs, traces, context diff

Launch with: streamlit run frontend/app.py
"""

import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from db.connection import init_db, get_connection, DB_PATH
from db.repository import (
    SettingsRepository,
    RunRepository,
    StepRepository,
    SpecResultRepository,
    ContextSnapshotRepository,
    TraceRepository,
    ItemRepository,
)
from frontend.components.spec_badge import render_spec_group
from frontend.components.context_diff import render_context_diff

init_db()

st.set_page_config(
    page_title="Spec-Agent Workflow",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Load saved settings into session state ---
if "settings_loaded" not in st.session_state:
    conn = get_connection()
    repo = SettingsRepository()
    st.session_state["api_key"] = repo.get(conn, "openai_api_key") or ""
    st.session_state["model"] = repo.get(conn, "default_model") or "gpt-4o"
    st.session_state["input_folder"] = repo.get(conn, "default_input_folder") or str(
        PROJECT_ROOT / "data" / "input"
    )
    st.session_state["output_folder"] = repo.get(conn, "default_output_folder") or str(
        PROJECT_ROOT / "data" / "output"
    )
    conn.close()
    st.session_state["settings_loaded"] = True

# --- Sidebar ---
with st.sidebar:
    st.header("Quick Info")
    st.markdown(f"**DB:** `{DB_PATH.name}`")
    key_set = bool(st.session_state.get("api_key"))
    st.markdown(f"**API Key:** {':green[Set]' if key_set else ':red[Not set]'}")
    st.markdown(f"**Model:** `{st.session_state.get('model', 'gpt-4o')}`")
    st.markdown("---")
    st.caption("Spec-Agent v0.1.0")


# ==========================================================================
# DASHBOARD
# ==========================================================================

st.title("Spec-Agent Workflow System")

st.markdown("""
A **Spec-Pattern Multi-Agent Architecture** for structured text extraction.
The system loads text files, extracts structured items via an LLM, and writes
the results -- validating every step with pure specification functions and
recording a full execution trace to SQLite.
""")

st.page_link("pages/9_User_Guide.py", label="Getting Started -- User Guide", icon=":material/menu_book:")

# --- Quick Stats ---
conn = get_connection()
run_repo = RunRepository()
step_repo = StepRepository()
item_repo = ItemRepository()
spec_repo = SpecResultRepository()
ctx_repo = ContextSnapshotRepository()
trace_repo = TraceRepository()

all_runs = run_repo.list_runs(conn, limit=200)
all_items = item_repo.get_all(conn, limit=5000)

col_s1, col_s2, col_s3, col_s4 = st.columns(4)
with col_s1:
    st.metric("Total Runs", len(all_runs))
with col_s2:
    st.metric("Completed", sum(1 for r in all_runs if r["status"] == "completed"))
with col_s3:
    st.metric("Failed", sum(1 for r in all_runs if r["status"] == "failed"))
with col_s4:
    st.metric("Items Extracted", len(all_items))

st.markdown("---")

# --- No runs yet? Show call-to-action ---
if not all_runs:
    st.info("No workflow runs yet. Start your first run below.")
    st.page_link("pages/1_Run_Workflow.py", label="Go to Run Workflow")
    conn.close()
    st.stop()


# ==========================================================================
# LAST EXECUTED FLOW
# ==========================================================================

last_run = all_runs[0]
run_id = last_run["id"]

# Status badge
status = last_run["status"]
status_badge = {
    "completed": ":green[COMPLETED]",
    "failed": ":red[FAILED]",
    "running": ":orange[RUNNING]",
}.get(status, status.upper())

# Duration
duration_str = ""
if last_run["started_at"] and last_run.get("finished_at"):
    try:
        t0 = datetime.fromisoformat(last_run["started_at"])
        t1 = datetime.fromisoformat(last_run["finished_at"])
        duration_str = f"{(t1 - t0).total_seconds():.1f}s"
    except Exception:
        pass

st.subheader("Last Workflow Run")

col_r1, col_r2, col_r3, col_r4 = st.columns(4)
with col_r1:
    st.markdown(f"**Status:** {status_badge}")
with col_r2:
    st.markdown(f"**Manifest:** `{last_run['manifest_name']}`")
with col_r3:
    st.markdown(f"**Model:** `{last_run['model_name']}`")
with col_r4:
    st.markdown(f"**Duration:** {duration_str}")

st.caption(
    f"Run ID: `{run_id[:12]}...` | "
    f"Started: {last_run['started_at'][:19]}"
)

# --- Build step data ---
steps = step_repo.get_steps_for_run(conn, run_id)

step_map: dict[str, list] = {}
step_order: list[str] = []
for step in steps:
    name = step["step_name"]
    if name not in step_map:
        step_map[name] = []
        step_order.append(name)
    step_map[name].append(step)

# Final status per step (passed wins over failed)
step_final_status = {}
for name, execs in step_map.items():
    if any(e["status"] == "passed" for e in execs):
        step_final_status[name] = "passed"
    elif any(e["status"] == "failed" for e in execs):
        step_final_status[name] = "failed"
    else:
        step_final_status[name] = execs[-1]["status"]

# --- Mermaid Flow Diagram ---
try:
    from core.manifest import Manifest
    manifest = Manifest.from_yaml(PROJECT_ROOT / "manifests" / "text_extraction.yaml")
    edge_dicts = [
        {"from": e.from_step, "to": e.to_step, "condition": e.condition}
        for e in manifest.edges
    ]
except Exception:
    edge_dicts = []

lines = ["graph LR"]
for name in step_order:
    lines.append(f'    {name}["{name}"]')
for edge in edge_dicts:
    f, t = edge["from"], edge["to"]
    if t == "__end__":
        continue
    if edge.get("condition") == "on_fail":
        lines.append(f"    {f} -.->|fail| {t}")
    else:
        lines.append(f"    {f} -->|pass| {t}")
for name in step_order:
    s = step_final_status.get(name, "pending")
    if s == "passed":
        lines.append(f"    style {name} fill:#d4edda,stroke:#28a745,stroke-width:2px,color:#155724")
    elif s == "failed":
        lines.append(f"    style {name} fill:#f8d7da,stroke:#dc3545,stroke-width:2px,color:#721c24")
    else:
        lines.append(f"    style {name} fill:#e2e3e5,stroke:#6c757d,stroke-width:1px")

st.markdown("```mermaid\n" + "\n".join(lines) + "\n```")

# --- Clickable Step Buttons ---
st.caption("Select a step to inspect:")
btn_cols = st.columns(len(step_order))
for i, name in enumerate(step_order):
    s = step_final_status.get(name, "pending")
    attempts = len(step_map[name])

    # Build label
    if s == "passed":
        label = f"  {name}  |  OK  "
    elif s == "failed":
        label = f"  {name}  |  FAIL  "
    else:
        label = f"  {name}  "
    if attempts > 1:
        label += f"  ({attempts}x)"

    with btn_cols[i]:
        btn_type = "primary" if st.session_state.get("dashboard_selected_step") == name else "secondary"
        if st.button(label, key=f"step_btn_{name}", use_container_width=True, type=btn_type):
            st.session_state["dashboard_selected_step"] = name
            st.rerun()


# ==========================================================================
# SELECTED STEP DETAIL (inline)
# ==========================================================================

selected_step = st.session_state.get("dashboard_selected_step")

if selected_step and selected_step in step_map:
    st.markdown("---")
    executions = step_map[selected_step]

    for step_exec in executions:
        step_db_id = step_exec["id"]
        attempt = step_exec["attempt"]
        s = step_exec["status"]
        agent = step_exec["agent_name"]
        error = step_exec.get("error_message", "")
        summary = step_exec.get("output_summary", "")

        # Duration
        d_str = ""
        if step_exec["started_at"] and step_exec.get("finished_at"):
            try:
                t0 = datetime.fromisoformat(step_exec["started_at"])
                t1 = datetime.fromisoformat(step_exec["finished_at"])
                d_str = f"{(t1 - t0).total_seconds():.2f}s"
            except Exception:
                pass

        if s == "passed":
            badge = f":green[PASSED] in {d_str}"
        elif s == "failed":
            badge = f":red[FAILED] after {d_str}"
        else:
            badge = f":orange[{s.upper()}]"

        st.subheader(f"Step: {selected_step} -- Attempt {attempt}")
        st.markdown(f"**Status:** {badge} | **Agent:** `{agent}`")

        if summary:
            st.success(f"Result: {summary}")
        if error:
            st.error(error)

        # --- Spec Results ---
        spec_results = spec_repo.get_for_step(conn, step_db_id)
        pre_specs = [r for r in spec_results if r["spec_type"] == "pre"]
        post_specs = [r for r in spec_results if r["spec_type"] == "post"]
        inv_specs = [r for r in spec_results if r["spec_type"] == "invariant"]

        st.markdown("#### Specification Checks")
        c1, c2, c3 = st.columns(3)
        with c1:
            render_spec_group("Pre-Specs", pre_specs)
        with c2:
            render_spec_group("Post-Specs", post_specs)
        with c3:
            render_spec_group("Invariants", inv_specs)

        # --- Agent Traces ---
        traces = trace_repo.get_for_step(conn, step_db_id)
        if traces:
            st.markdown("#### Agent Actions")
            for trace in traces:
                t_type = trace["trace_type"]
                t_dur = trace.get("duration_ms")
                t_tokens = trace.get("tokens_used")
                t_model = trace.get("model_name", "")
                t_input = trace.get("input_data", "")
                t_output = trace.get("output_data", "")

                parts = [f"`{t_type}`"]
                if t_model:
                    parts.append(f"model=`{t_model}`")
                if t_dur:
                    parts.append(f"{t_dur}ms")
                if t_tokens:
                    parts.append(f"{t_tokens} tokens")
                st.markdown("- " + " | ".join(parts))

                if t_input or t_output:
                    dc = st.columns(2)
                    if t_input:
                        with dc[0]:
                            with st.popover("Show Input"):
                                st.code(t_input[:2000], language="text")
                    if t_output:
                        with dc[1]:
                            with st.popover("Show Output"):
                                st.code(t_output[:2000], language="text")

        # --- Context Diff ---
        snapshots = ctx_repo.get_for_step(conn, step_db_id)
        before = after = None
        for snap in snapshots:
            if snap["snapshot_type"] == "before":
                before = snap["data_json"]
            elif snap["snapshot_type"] == "after":
                after = snap["data_json"]

        if before is not None and after is not None:
            st.markdown("#### Context Changes")
            render_context_diff(before, after)

        if len(executions) > 1:
            st.markdown("---")

else:
    st.markdown("---")
    st.caption(
        "Click a step above to inspect its specification checks, "
        "agent traces, and context changes."
    )


# ==========================================================================
# QUICK LINKS
# ==========================================================================

st.markdown("---")
lc1, lc2, lc3, lc4 = st.columns(4)
with lc1:
    st.page_link("pages/1_Run_Workflow.py", label="Run New Workflow")
with lc2:
    if st.button("Full Run Detail"):
        st.session_state["selected_run_id"] = run_id
        st.switch_page("pages/3_Run_Detail.py")
with lc3:
    st.page_link("pages/9_User_Guide.py", label="User Guide")
with lc4:
    st.page_link("pages/6_Architecture.py", label="Architecture")

conn.close()
