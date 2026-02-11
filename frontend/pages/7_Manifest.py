"""Page 7: Manifest Viewer.

Interactive view of the workflow manifest:
- Raw YAML source
- Parsed step definitions with linked spec details
- Graph visualization from edges
- Defaults and budgets
"""

import sys
import inspect
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import yaml

from core.manifest import Manifest
from core.specs import get_spec, _SPEC_REGISTRY
from core.agents import list_agents

# Ensure agents are registered
import agents  # noqa: F401

st.header("Manifest Viewer")
st.markdown(
    "The **manifest** is the source of truth for a workflow. "
    "It defines steps, agents, specs, edges, and budgets as **data** (YAML), not code."
)

# --- List available manifests ---
manifests_dir = PROJECT_ROOT / "manifests"
manifest_files = sorted(manifests_dir.glob("*.yaml"))

if not manifest_files:
    st.error("No manifest files found in manifests/ directory.")
    st.stop()

selected_file = st.selectbox(
    "Select Manifest",
    options=manifest_files,
    format_func=lambda p: p.stem,
)

# --- Load manifest ---
manifest = Manifest.from_yaml(selected_file)
raw_yaml = selected_file.read_text(encoding="utf-8")

# ==========================================================================
# OVERVIEW
# ==========================================================================

st.markdown("---")
st.subheader("Overview")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Name", manifest.name)
with col2:
    st.metric("Version", manifest.version)
with col3:
    st.metric("Steps", len(manifest.steps))
with col4:
    st.metric("Edges", len(manifest.edges))

st.markdown(f"**Description:** {manifest.description}")
st.markdown(f"**Entry Step:** `{manifest.entry_step}`")

# ==========================================================================
# FLOW GRAPH
# ==========================================================================

st.markdown("---")
st.subheader("Workflow Graph")

lines = ["graph LR"]
for name in manifest.steps:
    step = manifest.steps[name]
    agent = step.agent_name
    lines.append(f'    {name}["{name}<br/><small>{agent}</small>"]')

for edge in manifest.edges:
    f, t = edge.from_step, edge.to_step
    cond = edge.condition
    if t == "__end__":
        lines.append(f'    {f} -->|{cond}| END(("end"))')
    elif cond == "on_fail":
        lines.append(f"    {f} -.->|{cond}| {t}")
    else:
        lines.append(f"    {f} -->|{cond}| {t}")

# Highlight entry step
lines.append(f"    style {manifest.entry_step} fill:#e1f5fe,stroke:#0288d1,stroke-width:3px")

st.markdown("```mermaid\n" + "\n".join(lines) + "\n```")

# ==========================================================================
# STEPS DETAIL
# ==========================================================================

st.markdown("---")
st.subheader("Step Definitions")

for step_name, step_def in manifest.steps.items():
    is_entry = step_name == manifest.entry_step
    entry_badge = " (entry)" if is_entry else ""

    with st.expander(f"**{step_name}**{entry_badge} -- agent: `{step_def.agent_name}`", expanded=False):
        # Agent info
        st.markdown(f"**Agent:** `{step_def.agent_name}`")
        st.markdown(
            f"**Retry Policy:** max {step_def.retry.max_attempts} attempts, "
            f"{step_def.retry.delay_seconds}s delay"
        )

        # Specs table
        st.markdown("#### Specifications")

        spec_rows = []
        for spec_name in step_def.pre_specs:
            spec_rows.append(("pre", spec_name))
        for spec_name in step_def.post_specs:
            spec_rows.append(("post", spec_name))
        for spec_name in step_def.invariant_specs:
            spec_rows.append(("invariant", spec_name))

        if spec_rows:
            for spec_type, spec_name in spec_rows:
                col_a, col_b = st.columns([1, 3])
                with col_a:
                    if spec_type == "pre":
                        st.markdown(f":blue[{spec_type}]")
                    elif spec_type == "post":
                        st.markdown(f":green[{spec_type}]")
                    else:
                        st.markdown(f":orange[{spec_type}]")
                with col_b:
                    st.markdown(f"`{spec_name}`")
                    # Show the spec's docstring
                    try:
                        fn = get_spec(spec_name)
                        doc = fn.__doc__
                        if doc:
                            st.caption(doc.strip().split("\n")[0])
                    except KeyError:
                        st.caption(":red[Spec not found in registry]")

        # Show outgoing edges from this step
        st.markdown("#### Outgoing Edges")
        outgoing = [e for e in manifest.edges if e.from_step == step_name]
        if outgoing:
            for edge in outgoing:
                target = edge.to_step if edge.to_step != "__end__" else "END"
                st.markdown(f"- **{edge.condition}** -> `{target}`")
        else:
            st.caption("No outgoing edges (terminal step or implicit end)")

# ==========================================================================
# SPEC REGISTRY
# ==========================================================================

st.markdown("---")
st.subheader("Spec Registry")
st.markdown("All registered specification functions and their source code.")

for spec_name in sorted(_SPEC_REGISTRY.keys()):
    fn = _SPEC_REGISTRY[spec_name]
    doc = (fn.__doc__ or "").strip().split("\n")[0]

    with st.expander(f"`{spec_name}` -- {doc}"):
        source = inspect.getsource(fn)
        # Remove the decorator line for cleaner display
        source_lines = source.split("\n")
        cleaned = "\n".join(
            line for line in source_lines
            if not line.strip().startswith("@register_spec")
        )
        st.code(cleaned.strip(), language="python")

# ==========================================================================
# AGENT REGISTRY
# ==========================================================================

st.markdown("---")
st.subheader("Agent Registry")
st.markdown("All registered agents available for use in manifests.")

registered = list_agents()
for agent_name in sorted(registered):
    from core.agents import _AGENT_REGISTRY
    cls = _AGENT_REGISTRY[agent_name]
    doc = (cls.__doc__ or "No description").strip().split("\n")[0]
    st.markdown(f"- `{agent_name}` -- {doc}")

# ==========================================================================
# DEFAULTS & BUDGETS
# ==========================================================================

st.markdown("---")
col_d, col_b = st.columns(2)

with col_d:
    st.subheader("Defaults")
    if manifest.defaults:
        for key, val in manifest.defaults.items():
            st.markdown(f"- **{key}:** `{val}`")
    else:
        st.caption("No defaults defined.")

with col_b:
    st.subheader("Budgets")
    if manifest.budgets:
        for key, val in manifest.budgets.items():
            st.markdown(f"- **{key}:** `{val}`")
    else:
        st.caption("No budgets defined.")

# ==========================================================================
# RAW YAML
# ==========================================================================

st.markdown("---")
st.subheader("Raw YAML Source")
st.code(raw_yaml, language="yaml")
