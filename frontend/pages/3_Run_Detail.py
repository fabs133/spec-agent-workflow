"""Page 3: Deep-dive into a specific run - step by step trace viewer."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from db.connection import get_connection, init_db
from db.repository import (
    RunRepository,
    StepRepository,
    SpecResultRepository,
    ContextSnapshotRepository,
    TraceRepository,
    ItemRepository,
)
from frontend.components.step_card import render_step_card
from frontend.components.flow_diagram import render_flow_diagram
from frontend.components.trace_timeline import render_trace_timeline

init_db()

st.header("Run Detail")

# Get run ID from session state or input
run_id = st.session_state.get("selected_run_id", "")
run_id_input = st.text_input("Run ID", value=run_id, help="Paste a run ID or select from Run History")

if not run_id_input:
    st.info("Select a run from Run History or paste a Run ID above.")
    st.stop()

conn = get_connection()
run_repo = RunRepository()
step_repo = StepRepository()
spec_repo = SpecResultRepository()
ctx_repo = ContextSnapshotRepository()
trace_repo = TraceRepository()
item_repo = ItemRepository()

run = run_repo.get_run(conn, run_id_input)
if not run:
    st.error(f"Run not found: {run_id_input}")
    conn.close()
    st.stop()

# --- Run Summary ---
st.subheader("Run Summary")

status = run["status"]
if status == "completed":
    st.success(f"Status: COMPLETED")
elif status == "failed":
    st.error(f"Status: FAILED - {run.get('error_message', '')}")
else:
    st.info(f"Status: {status.upper()}")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Manifest", run["manifest_name"])
with col2:
    st.metric("Model", run["model_name"])
with col3:
    st.metric("Steps", f"{run['completed_steps']}/{run['total_steps']}")
with col4:
    items = item_repo.get_for_run(conn, run_id_input)
    st.metric("Items Extracted", len(items))

st.markdown(f"**Run ID:** `{run['id']}`")
st.markdown(f"**Started:** {run['started_at'][:19]}")
if run["finished_at"]:
    st.markdown(f"**Finished:** {run['finished_at'][:19]}")

# --- Flow Diagram ---
st.markdown("---")
st.subheader("Flow Diagram")

steps = step_repo.get_steps_for_run(conn, run_id_input)

# Build step statuses for diagram
step_statuses = {}
step_order = []
for step in steps:
    name = step["step_name"]
    if name not in step_statuses or step["status"] == "passed":
        step_statuses[name] = step["status"]
    if name not in step_order:
        step_order.append(name)

# Get edges from manifest
from core.manifest import Manifest
manifest_path = PROJECT_ROOT / "manifests" / "text_extraction.yaml"
try:
    manifest = Manifest.from_yaml(manifest_path)
    edge_dicts = [{"from": e.from_step, "to": e.to_step, "condition": e.condition}
                  for e in manifest.edges]
except Exception:
    edge_dicts = []

render_flow_diagram(step_order, edge_dicts, step_statuses)

# --- Step-by-Step Accordion ---
st.markdown("---")
st.subheader("Step-by-Step Execution")

for step in steps:
    step_id = step["id"]
    spec_results = spec_repo.get_for_step(conn, step_id)
    context_snapshots = ctx_repo.get_for_step(conn, step_id)
    agent_traces = trace_repo.get_for_step(conn, step_id)

    render_step_card(step, spec_results, context_snapshots, agent_traces)

# --- Full Trace Timeline ---
st.markdown("---")
st.subheader("Full Trace Timeline")

all_traces = trace_repo.get_for_run(conn, run_id_input)
render_trace_timeline(all_traces)

# --- Extracted Items ---
if items:
    st.markdown("---")
    st.subheader("Extracted Items")

    for item in items:
        with st.expander(f"**{item['title']}** ({item['item_type']}) - {item['confidence']:.0%}"):
            st.markdown(f"**Type:** {item['item_type']}")
            st.markdown(f"**Source:** {item.get('source_file', 'N/A')}")
            st.markdown(f"**Confidence:** {item['confidence']:.0%}")
            tags = item.get("tags", [])
            if tags:
                st.markdown(f"**Tags:** {', '.join(tags)}")
            st.markdown(f"**Description:** {item.get('description', 'N/A')}")

conn.close()
