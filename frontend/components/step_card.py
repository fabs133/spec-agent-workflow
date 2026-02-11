"""Step card component: renders a single step execution as an expandable card."""

from __future__ import annotations

from typing import Dict, List

import streamlit as st

from frontend.components.spec_badge import render_spec_group
from frontend.components.context_diff import render_context_diff


def render_step_card(
    step: Dict,
    spec_results: List[Dict],
    context_snapshots: List[Dict],
    agent_traces: List[Dict],
) -> None:
    """Render a detailed step execution card.

    Args:
        step: Step execution dict from DB.
        spec_results: All spec results for this step.
        context_snapshots: Before/after context snapshots.
        agent_traces: Agent trace entries for this step.
    """
    status = step.get("status", "pending")
    name = step.get("step_name", "unknown")
    agent = step.get("agent_name", "unknown")
    attempt = step.get("attempt", 1)
    error = step.get("error_message", "")
    summary = step.get("output_summary", "")

    # Compute duration
    started = step.get("started_at", "")
    finished = step.get("finished_at", "")
    duration_str = ""
    if started and finished:
        try:
            from datetime import datetime
            t0 = datetime.fromisoformat(started)
            t1 = datetime.fromisoformat(finished)
            dur = (t1 - t0).total_seconds()
            duration_str = f"{dur:.1f}s"
        except Exception:
            pass

    # Header with status indicator
    if status == "passed":
        icon = "OK"
        header = f":green[{icon}] **{name}** (Attempt {attempt}) -- {duration_str}"
    elif status == "failed":
        icon = "FAIL"
        header = f":red[{icon}] **{name}** (Attempt {attempt}) -- {duration_str}"
    elif status == "running":
        header = f":orange[...] **{name}** (Attempt {attempt})"
    else:
        header = f"**{name}** (Attempt {attempt})"

    with st.expander(header, expanded=(status == "failed")):
        # Agent info
        st.markdown(f"**Agent:** `{agent}`")
        if summary:
            st.markdown(f"**Result:** {summary}")
        if error:
            st.error(error)

        # Spec results grouped by type
        pre_specs = [s for s in spec_results if s.get("spec_type") == "pre"]
        post_specs = [s for s in spec_results if s.get("spec_type") == "post"]
        inv_specs = [s for s in spec_results if s.get("spec_type") == "invariant"]

        col1, col2, col3 = st.columns(3)
        with col1:
            render_spec_group("Pre-Specs", pre_specs)
        with col2:
            render_spec_group("Post-Specs", post_specs)
        with col3:
            render_spec_group("Invariants", inv_specs)

        # Agent traces
        if agent_traces:
            st.markdown("---")
            st.markdown("**Agent Traces:**")
            for trace in agent_traces:
                t_type = trace.get("trace_type", "unknown")
                t_input = trace.get("input_data", "")
                t_output = trace.get("output_data", "")
                t_dur = trace.get("duration_ms")
                t_tokens = trace.get("tokens_used")
                t_model = trace.get("model_name", "")

                parts = [f"`{t_type}`"]
                if t_model:
                    parts.append(f"model={t_model}")
                if t_dur:
                    parts.append(f"{t_dur}ms")
                if t_tokens:
                    parts.append(f"{t_tokens} tokens")
                st.markdown("&ensp; " + " | ".join(parts))

                if t_input:
                    with st.popover("Input"):
                        st.code(t_input[:1000], language="text")
                if t_output:
                    with st.popover("Output"):
                        st.code(t_output[:1000], language="text")

        # Context diff
        before = None
        after = None
        for snap in context_snapshots:
            if snap.get("snapshot_type") == "before":
                before = snap.get("data_json", {})
            elif snap.get("snapshot_type") == "after":
                after = snap.get("data_json", {})

        if before is not None and after is not None:
            st.markdown("---")
            render_context_diff(before, after)
