"""Spec result badge component."""

from __future__ import annotations

from typing import Dict, List

import streamlit as st


def render_spec_badge(spec: Dict) -> None:
    """Render a single spec result as a colored badge."""
    passed = spec.get("passed", 0)
    name = spec.get("spec_name", spec.get("rule_id", "unknown"))
    detail = spec.get("detail", spec.get("message", ""))
    fix = spec.get("suggested_fix", "")

    if passed:
        st.markdown(f"&ensp; :green[PASS] **{name}**: {detail}")
    else:
        st.markdown(f"&ensp; :red[FAIL] **{name}**: {detail}")
        if fix:
            st.markdown(f"&ensp;&ensp; *Fix: {fix}*")


def render_spec_group(title: str, specs: List[Dict]) -> None:
    """Render a group of spec results with a header."""
    if not specs:
        return
    all_passed = all(s.get("passed", 0) for s in specs)
    icon = ":green[OK]" if all_passed else ":red[FAIL]"
    st.markdown(f"**{title}** {icon}")
    for spec in specs:
        render_spec_badge(spec)
