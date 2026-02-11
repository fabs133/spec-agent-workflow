"""Page 6: Interactive Architecture Explainer.

Educational page that explains the Spec-Pattern Multi-Agent Architecture
using real code from the project and interactive diagrams.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.header("Architecture Explainer")
st.markdown(
    "This page explains the **Spec-Pattern Multi-Agent Architecture** "
    "that powers this system. Each section shows real code from the project."
)

# --- 1. Overview ---
st.subheader("1. System Overview")
st.markdown("""
The architecture separates concerns into distinct components:

| Component | Role | Purity |
|-----------|------|--------|
| **Context** | Shared state container | Data only |
| **Specs** | Validation rules | Pure functions (no IO) |
| **Agents** | Execute tasks | IO allowed |
| **Router** | Choose next step | Logic only |
| **Manifest** | Define workflow graph | Data (YAML) |
| **Orchestrator** | Run everything | Coordination |
| **Database** | Store traces | Persistence |

The key insight: **the workflow graph is data** (YAML), not code.
Changing the workflow means editing a YAML file, not Python code.
""")

st.markdown("```mermaid\ngraph LR\n"
    "    Manifest[Manifest YAML] --> Orchestrator\n"
    "    Orchestrator --> Specs[Spec Engine]\n"
    "    Orchestrator --> Agents\n"
    "    Orchestrator --> Router\n"
    "    Orchestrator --> DB[(SQLite)]\n"
    "    Specs -.-> |validate| Agents\n"
    "    Router -.-> |next step| Orchestrator\n"
    "    style Manifest fill:#e1f5fe\n"
    "    style Specs fill:#e8f5e9\n"
    "    style Agents fill:#fff3e0\n"
    "    style DB fill:#f3e5f5\n"
    "```")

# --- 2. What is a Spec? ---
st.markdown("---")
st.subheader("2. What is a Spec?")
st.markdown("""
A **Spec** (Specification) is a **pure evaluation function**:
- No file IO, no network calls, no database access
- No mutation of input data (read-only)
- Deterministic: same input always produces same output
- Returns a structured result (passed/failed + message + suggested fix)

This makes specs **trivially testable** and **composable**.
""")

# Show real spec code
spec_file = PROJECT_ROOT / "core" / "specs.py"
if spec_file.exists():
    code = spec_file.read_text(encoding="utf-8")
    # Extract one spec function as example
    start = code.find('@register_spec("intake_pre")')
    end = code.find('@register_spec("intake_post")')
    if start > 0 and end > start:
        example = code[start:end].strip()
        st.code(example, language="python")

st.markdown("""
**Why this matters:**
- Specs can be tested with 100% determinism (29 tests, 0 mocking needed)
- Specs tell agents *why* something failed (not just "error")
- The `suggested_fix` field enables self-correction
""")

# --- 3. What is the Context? ---
st.markdown("---")
st.subheader("3. What is the Context?")
st.markdown("""
The **Context** is a shared state container passed through all steps.
Each step reads from it and adds new data.
""")

st.code("""
@dataclass
class Context:
    run_id: str                    # Unique workflow run ID
    data: Dict[str, Any]           # Mutable shared state
    artifacts: Dict[str, Any]      # Files, outputs
    trace: List[Dict[str, Any]]    # Execution log
    budgets: Dict[str, int]        # Retry/cost limits
    config: Dict[str, Any]         # API keys, model, etc.
""", language="python")

st.markdown("""
**Data flow through steps:**

| After Step | New Keys in context.data |
|-----------|--------------------------|
| Intake | `loaded_files` (list of file dicts) |
| Extract | `extracted_items` (list of item dicts) |
| Write | `written_files` (list of output paths) |

The database stores **snapshots** of context before and after each step,
enabling the "Context Diff" view you see in Run Detail.
""")

# --- 4. What is the Manifest? ---
st.markdown("---")
st.subheader("4. What is the Manifest?")
st.markdown("""
The **Manifest** is a YAML file that defines the entire workflow as data:
- Which steps exist
- Which agent runs at each step
- Which specs validate each step
- How steps connect (graph edges)
- Retry policies and budgets

**The graph is DATA, not code.** You can add a new step by editing YAML alone.
""")

manifest_file = PROJECT_ROOT / "manifests" / "text_extraction.yaml"
if manifest_file.exists():
    st.code(manifest_file.read_text(encoding="utf-8"), language="yaml")

# --- 5. The Orchestrator Loop ---
st.markdown("---")
st.subheader("5. The Orchestrator Loop")
st.markdown("""
The **Orchestrator** is the execution engine. For each step, it runs this loop:
""")

st.markdown("""
```
For each step in the graph:
  1. Check global invariants
  2. Run PRE-SPECS
     -> If fail: skip agent, record failure
  3. Snapshot context (BEFORE)
  4. Execute AGENT
  5. Snapshot context (AFTER)
  6. Run POST-SPECS
     -> If fail: compute fingerprint, retry if allowed
  7. Run INVARIANT-SPECS
     -> If fail: halt workflow
  8. Save everything to SQLite
  9. Notify frontend (callback)
  10. Use ROUTER to find next step
  11. Repeat
```
""")

st.markdown("""
```mermaid
graph TD
    A[Start Step] --> B{Pre-Specs Pass?}
    B -->|Yes| C[Execute Agent]
    B -->|No| H[Record Failure]
    C --> D{Post-Specs Pass?}
    D -->|Yes| E{Invariants Pass?}
    D -->|No| F{Retries Left?}
    E -->|Yes| G[Route to Next Step]
    E -->|No| I[Halt Workflow]
    F -->|Yes| J[Enrich Context + Retry]
    F -->|No| H
    J --> A
    H --> G
    style B fill:#e8f5e9
    style D fill:#e8f5e9
    style E fill:#e8f5e9
    style C fill:#fff3e0
    style G fill:#e1f5fe
```
""")

# --- 6. Loop Prevention ---
st.markdown("---")
st.subheader("6. Loop Prevention")
st.markdown("""
**Problem:** Agents can fail in repetitive patterns - same tool call, same invalid
output, same missing fields. Without controls, the system retries forever.

**Solution: Failure Fingerprinting**

After each failure, the system computes a hash of:
- Step name
- Context data keys
- Failed rule IDs

If the **same fingerprint repeats**, the retry is blocked (loop detected).
Retries are only allowed when the "situation changed":
- New data was added
- Different rules are failing
- Error information was enriched
""")

st.code("""
@staticmethod
def compute_fingerprint(step_id, context_data, failed_rule_ids):
    canonical = json.dumps({
        "step_id": step_id,
        "data_keys": sorted(context_data.keys()),
        "failed_rules": sorted(failed_rule_ids),
    }, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]
""", language="python")

# --- 7. Database Schema ---
st.markdown("---")
st.subheader("7. Database Schema")
st.markdown("""
The SQLite database stores every detail for visualization:
""")

st.markdown("""
```mermaid
erDiagram
    workflow_runs ||--o{ step_executions : contains
    workflow_runs ||--o{ extracted_items : produces
    step_executions ||--o{ spec_results : validates
    step_executions ||--o{ context_snapshots : captures
    step_executions ||--o{ agent_traces : logs

    workflow_runs {
        text id PK
        text manifest_name
        text status
        text started_at
        text finished_at
    }
    step_executions {
        text id PK
        text run_id FK
        text step_name
        int attempt
        text status
        text fingerprint
    }
    spec_results {
        text id PK
        text step_execution_id FK
        text spec_name
        text spec_type
        int passed
        text detail
    }
    context_snapshots {
        text id PK
        text step_execution_id FK
        text snapshot_type
        text data_json
    }
    agent_traces {
        text id PK
        text step_execution_id FK
        text trace_type
        int duration_ms
        int tokens_used
    }
    extracted_items {
        text id PK
        text run_id FK
        text title
        text item_type
        real confidence
    }
```
""")

st.markdown("""
**Key design choice:** `context_snapshots` stores the full context **before and after**
each step. This enables the "Context Diff" view in Run Detail, showing exactly
what each step added or changed.
""")

# --- 8. Test Stats ---
st.markdown("---")
st.subheader("8. Test Coverage")
st.markdown("""
The project has **82 unit tests** covering:

| Module | Tests | What's Tested |
|--------|-------|---------------|
| Specs | 29 | All spec functions, registry, determinism |
| Manifest | 23 | YAML loading, validation, router logic |
| Repository | 22 | All CRUD operations, foreign keys |
| Orchestrator | 8 | Happy path, failures, budgets, tracing |

Specs are the most testable part: **pure functions = zero mocking needed.**
""")
