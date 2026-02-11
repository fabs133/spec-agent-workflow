"""Context diff component: shows what changed between before/after snapshots."""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st


def render_context_diff(before: Dict[str, Any], after: Dict[str, Any]) -> None:
    """Render a visual diff of context data before and after a step.

    Shows:
    - Added keys (green)
    - Changed values (yellow)
    - Removed keys (red, unlikely but handled)
    """
    all_keys = sorted(set(list(before.keys()) + list(after.keys())))

    changes = []
    for key in all_keys:
        in_before = key in before
        in_after = key in after

        if not in_before and in_after:
            # New key added
            val = _format_value(after[key])
            changes.append(f"&ensp; :green[+ {key}]: {val}")
        elif in_before and not in_after:
            # Key removed
            changes.append(f"&ensp; :red[- {key}]")
        elif before[key] != after[key]:
            # Value changed
            before_val = _format_value(before[key])
            after_val = _format_value(after[key])
            changes.append(f"&ensp; :orange[~ {key}]: {before_val} -> {after_val}")

    if changes:
        st.markdown("**Context Changes:**")
        for change in changes:
            st.markdown(change)
    else:
        st.markdown("*No context changes*")


def _format_value(val: Any) -> str:
    """Format a value for display, truncating long values."""
    s = str(val)
    if len(s) > 120:
        return s[:120] + "..."
    return s
