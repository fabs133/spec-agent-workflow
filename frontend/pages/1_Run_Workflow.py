"""Page 1: Configure and run the workflow with live visualization."""

import sys
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from core.manifest import Manifest
from core.models import Context, StepStatus
from core.orchestrator import Orchestrator
from db.connection import get_connection, init_db
from db.repository import SettingsRepository
from frontend.components.flow_diagram import render_flow_diagram

init_db()

st.header("Run Workflow")

# --- Configuration Form ---
st.subheader("Configuration")

col1, col2 = st.columns(2)
with col1:
    input_folder = st.text_input(
        "Input Folder",
        value=st.session_state.get("input_folder", str(PROJECT_ROOT / "data" / "input")),
        help="Folder containing .txt and .md files to process",
    )
with col2:
    output_folder = st.text_input(
        "Output Folder",
        value=st.session_state.get("output_folder", str(PROJECT_ROOT / "data" / "output")),
        help="Folder where results will be written",
    )

col3, col4 = st.columns(2)
with col3:
    api_key = st.text_input(
        "OpenAI API Key",
        value=st.session_state.get("api_key", ""),
        type="password",
        help="Your OpenAI API key for GPT-4o",
    )
with col4:
    model = st.selectbox(
        "Model",
        options=["gpt-4o", "gpt-4o-mini", "gpt-4.1-nano", "gpt-3.5-turbo"],
        index=["gpt-4o", "gpt-4o-mini", "gpt-4.1-nano", "gpt-3.5-turbo"].index(
            st.session_state.get("model", "gpt-4o")
        ),
    )

# Save settings
if st.button("Save Settings"):
    conn = get_connection()
    repo = SettingsRepository()
    repo.set(conn, "openai_api_key", api_key)
    repo.set(conn, "default_model", model)
    repo.set(conn, "default_input_folder", input_folder)
    repo.set(conn, "default_output_folder", output_folder)
    conn.close()
    st.session_state["api_key"] = api_key
    st.session_state["model"] = model
    st.session_state["input_folder"] = input_folder
    st.session_state["output_folder"] = output_folder
    st.success("Settings saved!")

st.markdown("---")

# --- Show input files preview ---
input_path = Path(input_folder)
if input_path.exists():
    files = [f for f in sorted(input_path.iterdir())
             if f.is_file() and f.suffix.lower() in (".txt", ".md")]
    if files:
        st.markdown(f"**Input files found:** {len(files)}")
        for f in files:
            st.markdown(f"- `{f.name}` ({f.stat().st_size} bytes)")
    else:
        st.warning("No .txt or .md files found in the input folder.")
else:
    st.error(f"Input folder does not exist: {input_folder}")

st.markdown("---")

# --- Run Workflow ---
st.subheader("Execute Workflow")

# Load manifest
manifest_path = PROJECT_ROOT / "manifests" / "text_extraction.yaml"
manifest = Manifest.from_yaml(manifest_path)

# Show flow diagram (initial state)
step_names = [manifest.entry_step]
# Follow edges to get step order
current = manifest.entry_step
visited = {current}
from core.router import Router
router = Router(manifest.edges)
while True:
    next_s = router.next_step(current, step_passed=True)
    if not next_s or next_s == "__end__" or next_s in visited:
        break
    step_names.append(next_s)
    visited.add(next_s)
    current = next_s

edge_dicts = [{"from": e.from_step, "to": e.to_step, "condition": e.condition}
              for e in manifest.edges]

# Placeholders for live updates
diagram_placeholder = st.empty()
progress_placeholder = st.empty()
status_placeholder = st.empty()
steps_placeholder = st.container()

# Initial diagram
with diagram_placeholder.container():
    render_flow_diagram(step_names, edge_dicts)

if st.button("Start Workflow", type="primary", disabled=not api_key):
    if not api_key:
        st.error("Please set your OpenAI API key first.")
    else:
        # Build context
        context = Context(
            data={
                "input_folder": input_folder,
                "output_folder": output_folder,
            },
            config={
                "api_key": api_key,
                "model": model,
                "temperature": 0.3,
            },
        )

        conn = get_connection()
        orch = Orchestrator(manifest, conn)

        # Track step statuses for live diagram update
        step_statuses = {s: "pending" for s in step_names}
        step_results = []

        def on_step_update(attempt):
            """Callback: update UI after each step."""
            step_statuses[attempt.step_id] = attempt.status.value
            step_results.append(attempt)

            # Update flow diagram
            current = None
            for s in step_names:
                if step_statuses[s] == "pending":
                    current = s
                    break
            with diagram_placeholder.container():
                render_flow_diagram(step_names, edge_dicts, step_statuses, current)

            # Update progress
            done = sum(1 for s in step_statuses.values() if s == "passed")
            total = len(step_names)
            progress_placeholder.progress(done / total, text=f"Step {done}/{total}")

            # Show step result
            with steps_placeholder:
                status_icon = "OK" if attempt.status == StepStatus.PASSED else "FAIL"
                color = "green" if attempt.status == StepStatus.PASSED else "red"
                st.markdown(f":{color}[{status_icon}] **{attempt.step_id}** "
                           f"(attempt {attempt.attempt})")
                if attempt.error:
                    st.error(attempt.error)

                # Show spec results inline
                for r in attempt.pre_results:
                    icon = "green" if r.passed else "red"
                    st.markdown(f"&ensp; :{icon}[{'PASS' if r.passed else 'FAIL'}] "
                               f"pre: {r.rule_id} - {r.message}")
                for r in attempt.post_results:
                    icon = "green" if r.passed else "red"
                    st.markdown(f"&ensp; :{icon}[{'PASS' if r.passed else 'FAIL'}] "
                               f"post: {r.rule_id} - {r.message}")
                for r in attempt.invariant_results:
                    icon = "green" if r.passed else "red"
                    st.markdown(f"&ensp; :{icon}[{'PASS' if r.passed else 'FAIL'}] "
                               f"inv: {r.rule_id} - {r.message}")

        # Execute
        status_placeholder.info("Workflow running...")
        record = asyncio.run(orch.run(context, on_step_update=on_step_update))
        conn.close()

        # Final status
        if record.status.value == "completed":
            status_placeholder.success(
                f"Workflow completed! {len(record.steps)} step(s) executed. "
                f"Run ID: `{record.run_id[:8]}...`"
            )
            # Show extracted items count
            items = context.data.get("extracted_items", [])
            if items:
                st.markdown(f"**Extracted {len(items)} item(s).** "
                           "Go to *Run Detail* or *Items Browser* to inspect them.")
        else:
            status_placeholder.error(
                f"Workflow failed: {record.error}"
            )

        # Final diagram
        with diagram_placeholder.container():
            render_flow_diagram(step_names, edge_dicts, step_statuses)
elif not api_key:
    st.warning("Set an API key to enable workflow execution.")
