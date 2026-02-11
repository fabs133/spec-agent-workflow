"""Page 2: Browse past workflow runs."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from db.connection import get_connection, init_db
from db.repository import RunRepository, ItemRepository

init_db()

st.header("Run History")

conn = get_connection()
run_repo = RunRepository()
item_repo = ItemRepository()

runs = run_repo.list_runs(conn)

if not runs:
    st.info("No workflow runs yet. Go to 'Run Workflow' to start one.")
    conn.close()
    st.stop()

st.markdown(f"**{len(runs)} run(s) found**")

for run in runs:
    run_id = run["id"]
    status = run["status"]
    manifest = run["manifest_name"]
    started = run["started_at"]
    finished = run["finished_at"] or "..."
    model = run["model_name"]
    completed = run["completed_steps"]
    total = run["total_steps"]
    error = run["error_message"]

    # Duration
    duration_str = ""
    if run["started_at"] and run["finished_at"]:
        try:
            from datetime import datetime
            t0 = datetime.fromisoformat(run["started_at"])
            t1 = datetime.fromisoformat(run["finished_at"])
            dur = (t1 - t0).total_seconds()
            duration_str = f"{dur:.1f}s"
        except Exception:
            pass

    # Items count
    items = item_repo.get_for_run(conn, run_id)
    items_count = len(items)

    # Status color
    if status == "completed":
        status_display = ":green[COMPLETED]"
    elif status == "failed":
        status_display = ":red[FAILED]"
    elif status == "running":
        status_display = ":orange[RUNNING]"
    else:
        status_display = status

    with st.expander(
        f"{status_display} | {manifest} | {started[:19]} | "
        f"{completed}/{total} steps | {items_count} items | {duration_str}"
    ):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Run ID:** `{run_id[:12]}...`")
            st.markdown(f"**Model:** {model}")
        with col2:
            st.markdown(f"**Input:** `{run['input_folder']}`")
            st.markdown(f"**Output:** `{run['output_folder']}`")
        with col3:
            st.markdown(f"**Started:** {started[:19]}")
            st.markdown(f"**Finished:** {finished[:19] if finished else 'N/A'}")

        if error:
            st.error(f"Error: {error}")

        # Button to view details
        if st.button(f"View Details", key=f"detail_{run_id}"):
            st.session_state["selected_run_id"] = run_id
            st.switch_page("pages/3_Run_Detail.py")

conn.close()
