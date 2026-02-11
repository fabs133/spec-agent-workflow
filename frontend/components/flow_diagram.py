"""Flow diagram component using Mermaid syntax rendered via st.markdown."""

from __future__ import annotations

from typing import Dict, List, Optional

import streamlit as st


def render_flow_diagram(
    steps: List[str],
    edges: List[dict],
    step_statuses: Optional[Dict[str, str]] = None,
    current_step: Optional[str] = None,
) -> None:
    """Render a Mermaid flow diagram of the workflow.

    Args:
        steps: List of step names in order.
        edges: List of edge dicts with from/to/condition.
        step_statuses: Map of step_name -> status (passed/failed/running/pending).
        current_step: Currently executing step name.
    """
    statuses = step_statuses or {}
    lines = ["graph LR"]

    # Define nodes with styling
    for step in steps:
        status = statuses.get(step, "pending")
        if step == current_step:
            label = f"{step} ..."
            lines.append(f'    {step}["{label}"]')
        elif status == "passed":
            lines.append(f'    {step}["{step} OK"]')
        elif status == "failed":
            lines.append(f'    {step}["{step} FAIL"]')
        else:
            lines.append(f'    {step}["{step}"]')

    # Define edges
    for edge in edges:
        from_s = edge.get("from_step", edge.get("from", ""))
        to_s = edge.get("to_step", edge.get("to", ""))
        condition = edge.get("condition", "on_pass")
        if to_s == "__end__":
            continue
        if condition == "on_pass":
            lines.append(f"    {from_s} --> {to_s}")
        elif condition == "on_fail":
            lines.append(f"    {from_s} -.-> {to_s}")
        else:
            lines.append(f"    {from_s} --> {to_s}")

    # Style nodes based on status
    for step in steps:
        status = statuses.get(step, "pending")
        if step == current_step:
            lines.append(f"    style {step} fill:#fff3cd,stroke:#ffc107,stroke-width:3px")
        elif status == "passed":
            lines.append(f"    style {step} fill:#d4edda,stroke:#28a745,stroke-width:2px")
        elif status == "failed":
            lines.append(f"    style {step} fill:#f8d7da,stroke:#dc3545,stroke-width:2px")
        else:
            lines.append(f"    style {step} fill:#e2e3e5,stroke:#6c757d,stroke-width:1px")

    mermaid_code = "\n".join(lines)
    st.markdown(f"```mermaid\n{mermaid_code}\n```")
