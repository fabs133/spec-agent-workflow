-- Spec-Agent Workflow Database Schema
-- 7 tables capturing every detail of workflow execution for visualization.

CREATE TABLE IF NOT EXISTS workflow_runs (
    id              TEXT PRIMARY KEY,
    manifest_name   TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    input_folder    TEXT NOT NULL,
    output_folder   TEXT NOT NULL,
    model_name      TEXT NOT NULL DEFAULT 'gpt-4o',
    total_steps     INTEGER DEFAULT 0,
    completed_steps INTEGER DEFAULT 0,
    error_message   TEXT,
    config_json     TEXT
);

CREATE TABLE IF NOT EXISTS step_executions (
    id              TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES workflow_runs(id),
    step_name       TEXT NOT NULL,
    agent_name      TEXT NOT NULL,
    attempt         INTEGER NOT NULL DEFAULT 1,
    status          TEXT NOT NULL DEFAULT 'pending',
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    error_message   TEXT,
    output_summary  TEXT,
    fingerprint     TEXT
);

CREATE TABLE IF NOT EXISTS spec_results (
    id                TEXT PRIMARY KEY,
    step_execution_id TEXT NOT NULL REFERENCES step_executions(id),
    spec_name         TEXT NOT NULL,
    spec_type         TEXT NOT NULL,
    passed            INTEGER NOT NULL,
    detail            TEXT,
    suggested_fix     TEXT,
    evaluated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS context_snapshots (
    id                TEXT PRIMARY KEY,
    step_execution_id TEXT NOT NULL REFERENCES step_executions(id),
    snapshot_type     TEXT NOT NULL,
    data_json         TEXT NOT NULL,
    artifacts_json    TEXT,
    captured_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_traces (
    id                TEXT PRIMARY KEY,
    step_execution_id TEXT NOT NULL REFERENCES step_executions(id),
    trace_type        TEXT NOT NULL,
    timestamp         TEXT NOT NULL,
    input_data        TEXT,
    output_data       TEXT,
    duration_ms       INTEGER,
    tokens_used       INTEGER,
    model_name        TEXT
);

CREATE TABLE IF NOT EXISTS extracted_items (
    id              TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES workflow_runs(id),
    title           TEXT NOT NULL,
    item_type       TEXT NOT NULL,
    description     TEXT,
    tags            TEXT,
    source_file     TEXT,
    confidence      REAL DEFAULT 0.8,
    raw_json        TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
    key             TEXT PRIMARY KEY,
    value           TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_step_exec_run ON step_executions(run_id);
CREATE INDEX IF NOT EXISTS idx_spec_results_step ON spec_results(step_execution_id);
CREATE INDEX IF NOT EXISTS idx_context_snap_step ON context_snapshots(step_execution_id);
CREATE INDEX IF NOT EXISTS idx_traces_step ON agent_traces(step_execution_id);
CREATE INDEX IF NOT EXISTS idx_items_run ON extracted_items(run_id);
