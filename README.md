# Spec-Agent Workflow System

A **Spec-Pattern Multi-Agent Architecture** for structured text extraction, built as a school project (VP) demonstrating backend, frontend, and relational database integration.

The system loads text files, extracts structured items via an LLM, and writes the results -- validating every step with **pure specification functions** and recording a complete execution trace to a SQLite database.

**Standalone:** Zero external dependencies. Runs with Python 3.10+ only -- no `pip install` needed.

## Architecture

The design follows the **Specification Pattern** adapted for multi-agent workflows:

| Component       | Role                                      | Purity        |
|-----------------|-------------------------------------------|---------------|
| **Context**     | Shared state container passed through all steps | Data only     |
| **Specs**       | Pure validation functions (no IO, deterministic) | Pure          |
| **Agents**      | Execute tasks (file IO, LLM calls)        | IO allowed    |
| **Router**      | Choose next step based on spec outcomes   | Logic only    |
| **Manifest**    | Define the workflow graph as JSON data    | Data (JSON)   |
| **Orchestrator**| Execute the loop, enforce budgets, record traces | Coordination |
| **Database**    | Store execution traces for visualization  | Persistence   |

**Key principle:** The workflow graph is data (JSON), not code. Changing the workflow means editing a JSON file.

### Workflow Pipeline

```
  Intake              Extract              Write
 (load files)      (LLM extraction)     (save results)
     |                   |                   |
  pre-spec            pre-spec            pre-spec
  agent run           agent run           agent run
  post-spec           post-spec           post-spec
     |                   |                   |
     +--------->---------+--------->---------+
```

### Orchestrator Loop

For each step the orchestrator executes:

1. Check global invariants
2. Run **pre-specs** -- if fail, skip agent
3. Snapshot context (before)
4. Execute **agent**
5. Snapshot context (after)
6. Run **post-specs** -- if fail, retry with enriched context
7. Run **invariant-specs** -- if fail, halt workflow
8. Compute failure fingerprint for **loop detection**
9. Save everything to SQLite
10. Notify frontend via callback
11. Use **router** to find next step

## Tech Stack

- **Python 3.10+** (standard library only -- no pip dependencies)
- **Built-in HTTP server** -- Standalone web UI (no framework needed)
- **SQLite** -- Relational database for execution traces and settings
- **OpenAI API** -- LLM-powered text extraction (GPT-4o) via `urllib.request`

## Quick Start

### Run the Application

```bash
cd agent-workflow
python run.py
```

The browser opens automatically at `http://localhost:8501`.

To use a different port:

```bash
python run.py --port 8502
```

### First-Time Setup

1. Go to **Settings** and enter your OpenAI API key
2. Place `.txt` or `.md` files in the `data/input/` folder
3. Go to **Run Workflow** and click **Start Workflow**
4. Inspect results on the **Dashboard**, **Run Detail**, or **Items Browser**

### Run Tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

## Project Structure

```
agent-workflow/
├── run.py                 # Entry point: python run.py
├── core/                  # Spec-pattern engine
│   ├── models.py          # Context, SpecResult, StepAttempt, RunRecord
│   ├── specs.py           # Pure specification functions + registry
│   ├── agents.py          # BaseAgent ABC + registry
│   ├── steps.py           # StepDefinition dataclass
│   ├── router.py          # Edge selection logic
│   ├── manifest.py        # JSON -> in-memory graph
│   ├── orchestrator.py    # Main execution loop
│   ├── llm_client.py      # Stdlib OpenAI API client (urllib.request)
│   └── errors.py          # Custom exceptions
├── agents/                # Concrete agent implementations
│   ├── intake_agent.py    # Read text files from input folder
│   ├── extract_agent.py   # LLM-powered structured extraction
│   ├── write_agent.py     # Write JSON + Markdown output
│   └── prompts.py         # LLM prompt templates
├── db/                    # Database layer
│   ├── schema.sql         # 7 tables with foreign keys
│   ├── connection.py      # SQLite connection management
│   └── repository.py      # Repository classes (no ORM)
├── frontend_web/          # Standalone web UI (stdlib only)
│   ├── server.py          # HTTP server + JSON API endpoints
│   └── static/            # SPA frontend (HTML/CSS/JS)
│       ├── index.html     # App shell with sidebar navigation
│       ├── app.js         # All pages as JS render functions
│       └── style.css      # Dark theme styles
├── manifests/             # Workflow definitions (JSON)
│   └── text_extraction.json
├── tests/                 # 85 unit tests
│   ├── test_specs.py      # 29 tests -- pure spec functions
│   ├── test_manifest.py   # 23 tests -- JSON loading, router
│   ├── test_repository.py # 22 tests -- CRUD, foreign keys
│   ├── test_orchestrator.py # 8 tests -- execution loop
│   └── test_llm_client.py # 3 tests -- stdlib API client
├── data/
│   └── input/             # Sample input files
├── pyproject.toml
└── .env.example
```

## Frontend Pages

| Page | Description |
|------|-------------|
| **Dashboard** | Flow diagram of the last run with clickable steps |
| **Run Workflow** | Configure and launch a workflow with live progress |
| **Run History** | Browse all past workflow runs |
| **Run Detail** | Deep-dive into specs, traces, and context diffs |
| **Items Browser** | Search and filter all extracted items |
| **Settings** | API key, model, input/output folder configuration |
| **Architecture** | Architecture explainer with code examples |
| **Manifest** | Inspect the active workflow definition and spec registry |
| **User Guide** | Step-by-step usage guide with troubleshooting |

## Database Schema

7 tables in SQLite:

- `workflow_runs` -- Top-level run records
- `step_executions` -- One row per step attempt (including retries)
- `spec_results` -- Individual spec check outcomes
- `context_snapshots` -- Full context before/after each step
- `agent_traces` -- Agent action log (LLM calls, file operations)
- `extracted_items` -- The actual workflow output
- `app_settings` -- Persisted configuration

## Tests

All 85 tests pass with zero external dependencies (no API calls, no filesystem):

```
tests/test_specs.py         -- 29 tests (pure functions, zero mocking needed)
tests/test_manifest.py      -- 23 tests (JSON parsing, validation, routing)
tests/test_repository.py    -- 22 tests (in-memory SQLite, FK constraints)
tests/test_orchestrator.py  --  8 tests (mock agents, budget enforcement)
tests/test_llm_client.py    --  3 tests (urllib.request mocking)
```

## License

School project -- all rights reserved.
