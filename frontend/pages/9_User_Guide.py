"""Page 9: User Guide.

A user-friendly walkthrough explaining how to use the application,
from initial setup to inspecting results.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.header("User Guide")
st.markdown(
    "A step-by-step guide to setting up and using the "
    "**Spec-Agent Workflow System**."
)

# ── 1. Quick Start ──────────────────────────────────────────────
st.subheader("1. Quick Start")
st.markdown("""
Get up and running in three steps:

1. **Set your API key** -- Go to **Settings** and paste your OpenAI API key.
2. **Run a workflow** -- Go to **Run Workflow**, pick your input folder, and click *Start*.
3. **Inspect results** -- The dashboard shows the last run. Dive deeper with
   *Run Detail* or *Items Browser*.
""")

st.info(
    "The system ships with two sample input files in `data/input/`. "
    "You can run your first workflow right away without adding any files."
)

# ── 2. Settings ─────────────────────────────────────────────────
st.markdown("---")
st.subheader("2. Settings")
st.markdown("""
Open the **Settings** page from the sidebar to configure:

| Setting | Description | Default |
|---------|-------------|---------|
| **OpenAI API Key** | Required for the extraction step. Keys start with `sk-...` | -- |
| **Model** | Which OpenAI model to use | `gpt-4o` |
| **Input Folder** | Where to read `.txt` / `.md` files from | `data/input/` |
| **Output Folder** | Where to write extraction results | `data/output/` |

Settings are persisted in the SQLite database, so they survive restarts.
""")

st.page_link("pages/5_Settings.py", label="Open Settings")

# ── 3. Running a Workflow ───────────────────────────────────────
st.markdown("---")
st.subheader("3. Running a Workflow")
st.markdown("""
The **Run Workflow** page lets you launch the three-step extraction pipeline:
""")

st.markdown("""
```
  Intake          Extract          Write
 (load files)  (LLM extraction)  (save results)
     |               |               |
  pre-spec        pre-spec        pre-spec
  agent run       agent run       agent run
  post-spec       post-spec       post-spec
     |               |               |
     +--------->-----+--------->-----+
```
""")

st.markdown("""
**How it works:**

1. **Intake** -- Reads all `.txt` and `.md` files from the input folder into memory.
2. **Extract** -- Sends each file to the LLM with a structured prompt.
   The LLM returns tasks, features, bugs, decisions, and notes as JSON.
3. **Write** -- Saves a JSON summary and individual Markdown files to the output folder.

At every step, **specification functions** (specs) validate the context before and
after the agent runs. If a post-spec fails, the system retries with enriched error
information (up to the configured maximum).
""")

st.page_link("pages/1_Run_Workflow.py", label="Open Run Workflow")

# ── 4. Understanding Results ────────────────────────────────────
st.markdown("---")
st.subheader("4. Understanding the Results")

st.markdown("#### Dashboard")
st.markdown("""
The **Dashboard** (home page) shows:
- **Quick stats** -- total runs, completed, failed, items extracted.
- **Flow diagram** -- a visual graph of the last run with color-coded step status.
- **Clickable steps** -- select any step to see its spec checks, agent traces,
  and context changes inline.
""")

st.markdown("#### Run History")
st.markdown("""
Browse all past workflow runs in a table. Each row shows the date, status,
duration, and number of extracted items. Click a run to jump to its detail view.
""")

st.markdown("#### Run Detail")
st.markdown("""
The most detailed view. For each step attempt you can see:

- **Specification checks** -- Pre-specs, post-specs, and invariants with
  pass/fail badges and messages.
- **Agent traces** -- What the agent did: file reads, LLM calls (with prompt,
  response, tokens used, and duration).
- **Context diff** -- A side-by-side comparison of the context before and after
  the step, showing exactly what data was added or changed.
""")

st.markdown("#### Items Browser")
st.markdown("""
A searchable table of all extracted items across all runs. Filter by:
- **Type** -- task, feature, bug, decision, note
- **Confidence** -- how confident the LLM is in the extraction
- **Source file** -- which input file the item came from

Click an item to see its full description and raw JSON.
""")

# ── 5. Workflow Definition ──────────────────────────────────────
st.markdown("---")
st.subheader("5. Workflow Definition (Manifest)")
st.markdown("""
The workflow is defined in a **YAML manifest** file (`manifests/text_extraction.yaml`).
The manifest specifies:

- **Steps** -- which agent runs and which specs validate
- **Edges** -- how steps connect (on pass / on fail)
- **Retry policies** -- how many times to retry on failure
- **Budgets** -- maximum total steps to prevent infinite loops

You can inspect the active manifest on the **Manifest** page, which shows
the parsed steps, specs, agents, and the flow graph.
""")

st.page_link("pages/7_Manifest.py", label="Open Manifest Viewer")

# ── 6. Architecture ─────────────────────────────────────────────
st.markdown("---")
st.subheader("6. Architecture Overview")
st.markdown("""
The system follows the **Spec-Pattern Multi-Agent Architecture**:

| Concept | Purpose |
|---------|---------|
| **Context** | Shared state passed through all steps |
| **Specs** | Pure validation functions (no IO, deterministic) |
| **Agents** | Execute tasks (file IO, LLM calls) |
| **Router** | Choose next step based on spec outcomes |
| **Manifest** | Define the workflow graph as YAML data |
| **Orchestrator** | Execute the loop, enforce budgets, record traces |

For a detailed technical walkthrough with code examples, visit the
**Architecture** page. For auto-generated API documentation, visit the
**Documentation** page.
""")

col1, col2 = st.columns(2)
with col1:
    st.page_link("pages/6_Architecture.py", label="Architecture Explainer")
with col2:
    st.page_link("pages/8_Documentation.py", label="API Documentation (Sphinx)")

# ── 7. Troubleshooting ──────────────────────────────────────────
st.markdown("---")
st.subheader("7. Troubleshooting")

st.markdown("#### Common Issues")

st.markdown("""
**Extract step fails with `extract_pre` spec error**
> The API key is not set. Go to Settings and enter a valid OpenAI API key.

**Extract step fails with `extract_post` spec error after retries**
> The LLM did not return valid structured data. Try a different model (e.g.
> `gpt-4o` instead of `gpt-4o-mini`) or check that the input files contain
> meaningful text.

**Intake step fails with `intake_post` spec error**
> No `.txt` or `.md` files found in the input folder. Make sure the path is
> correct and contains readable text files.

**Write step fails with `write_pre` spec error**
> The output folder path is invalid or the extract step did not produce items.
> Check Settings for the correct output folder path.
""")

st.markdown("#### Resetting")
st.markdown("""
To start fresh:
- Delete `data/spec_agent.db` to clear all run history and settings.
- Delete the contents of `data/output/` to remove generated files.
- The database is re-created automatically on next launch.
""")

# ── 8. Running Tests ────────────────────────────────────────────
st.markdown("---")
st.subheader("8. Running Tests")
st.markdown("""
The project includes **82 unit tests**. Run them from the project root:
""")
st.code("pytest tests/ -v", language="bash")
st.markdown("""
| Module | Tests | Coverage |
|--------|-------|----------|
| Specs | 29 | All spec functions, registry, determinism |
| Manifest | 23 | YAML loading, validation, router logic |
| Repository | 22 | CRUD operations, foreign key constraints |
| Orchestrator | 8 | Happy path, failures, budgets, tracing |

All spec tests require **zero mocking** -- they are pure functions that take a
context and return a result.
""")
