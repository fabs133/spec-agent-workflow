# Spec-Agent Workflow: Standalone Migration (v0.2.0)

**Category:** technical
**Date:** 2026-02-12

## Summary

Migrated the Spec-Agent Workflow System from a Streamlit-based application with 3 pip dependencies (`openai`, `pyyaml`, `streamlit`) to a fully standalone application with **zero external dependencies** -- runs with Python 3.10+ standard library only.

## Motivation

The project is a school VP (Vertiefungsarbeit). School computers have Python and pip installed, but pip has **no network access**. Manually downloading wheel files with their dependency chains is error-prone and time-consuming. Making the app standalone eliminates this problem entirely.

## Changes

### 1. Replaced `openai` SDK with `urllib.request`

- Created `core/llm_client.py` (~50 lines) -- stdlib wrapper for the OpenAI chat completions API
- Uses `urllib.request.urlopen()` with `ssl.create_default_context()`
- POSTs JSON to `https://api.openai.com/v1/chat/completions`
- Returns `(content, total_tokens)` tuple
- Updated `agents/extract_agent.py` to use the new client

### 2. Replaced `pyyaml` with `json`

- Converted workflow manifest from YAML to JSON format
- `manifests/text_extraction.yaml` -> `manifests/text_extraction.json`
- Updated `core/manifest.py` -- `from_file()` uses `json.loads()` instead of `yaml.safe_load()`
- Backward-compatible `from_yaml()` alias kept for existing callers

### 3. Replaced `streamlit` with stdlib HTTP server + HTML/JS SPA

The entire Streamlit frontend (2,700 lines across 15 files) was replaced with:

**Backend:** `frontend_web/server.py` (~350 lines)
- `http.server.HTTPServer` with `BaseHTTPRequestHandler`
- 15+ JSON API endpoints for all CRUD operations
- Workflow execution via `threading.Thread` with polling status endpoint
- Static file serving for the SPA

**Frontend:** `frontend_web/static/` (3 files)
- `index.html` -- SPA shell with sidebar navigation
- `app.js` (~900 lines) -- All 9 pages as JavaScript render functions with hash-based routing
- `style.css` -- Dark theme with CSS custom properties

**Feature parity with Streamlit version:**
- Dashboard with metrics and flow diagram
- Live workflow execution with progress polling
- Run history and detail views
- Items browser with filtering
- Settings management
- Architecture explainer
- Manifest viewer with spec registry source code
- User guide

### 4. New entry point

`run.py` -- launches the server and opens the browser:
```bash
python run.py [--port 8501]
```

## Architecture Decision

### Why not PyInstaller?

PyInstaller was considered but rejected because:
- Streamlit + PyInstaller is notoriously problematic (Streamlit spawns subprocesses)
- Would still require building on a compatible Windows machine
- Results in large executables (100MB+)

### Why not just bundle wheels?

- Streamlit alone pulls in 30+ transitive dependencies
- Version conflicts are common and hard to debug without network access
- A single incompatible wheel can block the entire install

### Why stdlib HTTP server?

- Zero dependencies
- Good enough for a local single-user application
- The SPA pattern (JSON API + HTML/JS) is actually more responsive than Streamlit's re-run model
- Easy to understand for a school project

## Test Results

85 tests pass (82 original + 3 new for `llm_client`):

| Suite | Tests | Impact |
|-------|-------|--------|
| test_specs.py | 29 | No changes |
| test_manifest.py | 23 | Updated file paths (.yaml -> .json) |
| test_repository.py | 22 | No changes |
| test_orchestrator.py | 8 | No changes |
| test_llm_client.py | 3 | New -- mocks urllib.request |

## Patterns Learned

### Replacing `openai` SDK with raw HTTP

The OpenAI SDK is a convenience wrapper around a simple HTTP API. For basic chat completions, `urllib.request` works fine:

```python
payload = json.dumps({"model": model, "messages": messages}).encode()
req = urllib.request.Request(url, data=payload, headers={"Authorization": f"Bearer {key}"})
with urllib.request.urlopen(req) as resp:
    body = json.loads(resp.read())
    return body["choices"][0]["message"]["content"]
```

### Replacing Streamlit with stdlib

Key mapping: `st.session_state` -> JavaScript variables, `st.rerun()` -> `fetch()` + DOM update, `st.empty()` -> polling endpoint, `st.columns()` -> CSS grid, `st.expander()` -> `<details>`.

### Async workflow in a sync HTTP server

Run the async orchestrator in a `threading.Thread`:
```python
def run_workflow():
    record = asyncio.run(orch.run(context, on_step_update=callback))
thread = threading.Thread(target=run_workflow, daemon=True)
thread.start()
```

The callback writes to a shared dict protected by `threading.Lock`. The frontend polls a status endpoint every 1.5 seconds.
