"""Page 4: Browse all extracted items across all runs."""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from db.connection import get_connection, init_db
from db.repository import ItemRepository, RunRepository

init_db()

st.header("Items Browser")

conn = get_connection()
item_repo = ItemRepository()
run_repo = RunRepository()

# Filters
col1, col2, col3 = st.columns(3)

all_items = item_repo.get_all(conn, limit=500)

if not all_items:
    st.info("No extracted items yet. Run a workflow first.")
    conn.close()
    st.stop()

# Collect filter options
all_types = sorted(set(item.get("item_type", "note") for item in all_items))
all_tags = sorted(set(tag for item in all_items for tag in (item.get("tags") or [])))
all_runs = sorted(set(item.get("run_id", "") for item in all_items))

with col1:
    type_filter = st.multiselect("Filter by Type", options=all_types, default=all_types)
with col2:
    tag_filter = st.multiselect("Filter by Tag", options=all_tags)
with col3:
    min_confidence = st.slider("Min Confidence", 0.0, 1.0, 0.0, 0.05)

# Apply filters
filtered = all_items
if type_filter:
    filtered = [i for i in filtered if i.get("item_type") in type_filter]
if tag_filter:
    filtered = [i for i in filtered
                if any(t in (i.get("tags") or []) for t in tag_filter)]
filtered = [i for i in filtered if (i.get("confidence") or 0) >= min_confidence]

st.markdown(f"**Showing {len(filtered)} of {len(all_items)} items**")

# Display items
for item in filtered:
    title = item.get("title", "Untitled")
    item_type = item.get("item_type", "note")
    confidence = item.get("confidence", 0)
    source = item.get("source_file", "N/A")
    tags = item.get("tags", [])
    description = item.get("description", "")
    run_id = item.get("run_id", "")[:8]

    # Type badge colors
    type_colors = {
        "task": "blue",
        "feature": "green",
        "bug": "red",
        "note": "gray",
        "decision": "violet",
    }
    color = type_colors.get(item_type, "gray")

    with st.expander(f":{color}[{item_type.upper()}] **{title}** -- {confidence:.0%} -- {source}"):
        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.markdown(f"**Description:** {description}")
            if tags:
                tag_str = " ".join(f"`{t}`" for t in tags)
                st.markdown(f"**Tags:** {tag_str}")
        with col_b:
            st.markdown(f"**Confidence:** {confidence:.0%}")
            st.markdown(f"**Source File:** `{source}`")
            st.markdown(f"**Run:** `{run_id}...`")

        # Raw JSON
        with st.popover("Raw JSON"):
            raw = item.get("raw_json", "")
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except Exception:
                    pass
            st.json(raw)

conn.close()
