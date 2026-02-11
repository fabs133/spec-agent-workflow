"""Trace timeline component: shows a chronological list of all agent actions."""

from __future__ import annotations

from typing import Dict, List

import streamlit as st


def render_trace_timeline(traces: List[Dict]) -> None:
    """Render all agent traces as a timeline."""
    if not traces:
        st.info("No traces recorded for this run.")
        return

    for i, trace in enumerate(traces):
        t_type = trace.get("trace_type", "unknown")
        timestamp = trace.get("timestamp", "")
        duration = trace.get("duration_ms")
        tokens = trace.get("tokens_used")
        model = trace.get("model_name", "")
        input_data = trace.get("input_data", "")
        output_data = trace.get("output_data", "")

        # Icon based on type
        if t_type == "llm_call":
            icon = "LLM"
        elif t_type == "file_read":
            icon = "READ"
        elif t_type == "file_write":
            icon = "WRITE"
        else:
            icon = t_type.upper()

        # Summary line
        parts = [f"**[{icon}]**"]
        if timestamp:
            time_part = timestamp.split("T")[-1][:8] if "T" in timestamp else timestamp
            parts.append(time_part)
        if model:
            parts.append(f"`{model}`")
        if duration:
            parts.append(f"{duration}ms")
        if tokens:
            parts.append(f"{tokens} tokens")

        st.markdown(f"{i+1}. " + " | ".join(parts))

        # Expandable details
        if input_data or output_data:
            with st.expander("Details", expanded=False):
                if input_data:
                    st.markdown("**Input:**")
                    st.code(input_data[:2000], language="text")
                if output_data:
                    st.markdown("**Output:**")
                    st.code(output_data[:2000], language="text")
