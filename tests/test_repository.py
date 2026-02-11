"""Tests for the database repository layer.

Uses in-memory SQLite for speed and isolation.
"""

import json
import sqlite3
from pathlib import Path

import pytest

from core.models import SpecResult
from db.repository import (
    RunRepository,
    StepRepository,
    SpecResultRepository,
    ContextSnapshotRepository,
    TraceRepository,
    ItemRepository,
    SettingsRepository,
)

SCHEMA_PATH = Path(__file__).parent.parent / "db" / "schema.sql"


@pytest.fixture
def db():
    """Fresh in-memory SQLite database with schema applied."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    yield conn
    conn.close()


@pytest.fixture
def run_repo():
    return RunRepository()


@pytest.fixture
def step_repo():
    return StepRepository()


@pytest.fixture
def spec_repo():
    return SpecResultRepository()


@pytest.fixture
def ctx_repo():
    return ContextSnapshotRepository()


@pytest.fixture
def trace_repo():
    return TraceRepository()


@pytest.fixture
def item_repo():
    return ItemRepository()


@pytest.fixture
def settings_repo():
    return SettingsRepository()


# ---------------------------------------------------------------------------
# RunRepository
# ---------------------------------------------------------------------------

class TestRunRepository:
    def test_create_and_get_run(self, db, run_repo):
        run_id = run_repo.create_run(
            db, "run-1", "text_extraction", "/input", "/output"
        )
        run = run_repo.get_run(db, run_id)
        assert run is not None
        assert run["manifest_name"] == "text_extraction"
        assert run["status"] == "running"
        assert run["input_folder"] == "/input"

    def test_update_run_status(self, db, run_repo):
        run_repo.create_run(db, "run-1", "test", "/in", "/out")
        run_repo.update_run(db, "run-1", status="completed", completed_steps=3)
        run = run_repo.get_run(db, "run-1")
        assert run["status"] == "completed"
        assert run["completed_steps"] == 3
        assert run["finished_at"] is not None

    def test_update_run_error(self, db, run_repo):
        run_repo.create_run(db, "run-1", "test", "/in", "/out")
        run_repo.update_run(db, "run-1", status="failed", error_message="Spec failed")
        run = run_repo.get_run(db, "run-1")
        assert run["status"] == "failed"
        assert run["error_message"] == "Spec failed"

    def test_list_runs(self, db, run_repo):
        run_repo.create_run(db, "run-1", "test", "/in", "/out")
        run_repo.create_run(db, "run-2", "test", "/in", "/out")
        runs = run_repo.list_runs(db)
        assert len(runs) == 2

    def test_get_nonexistent_run(self, db, run_repo):
        assert run_repo.get_run(db, "nonexistent") is None


# ---------------------------------------------------------------------------
# StepRepository
# ---------------------------------------------------------------------------

class TestStepRepository:
    def test_create_and_get_steps(self, db, run_repo, step_repo):
        run_repo.create_run(db, "run-1", "test", "/in", "/out")
        step_id = step_repo.create_step(db, "run-1", "intake", "IntakeAgent")
        steps = step_repo.get_steps_for_run(db, "run-1")
        assert len(steps) == 1
        assert steps[0]["step_name"] == "intake"
        assert steps[0]["agent_name"] == "IntakeAgent"

    def test_update_step(self, db, run_repo, step_repo):
        run_repo.create_run(db, "run-1", "test", "/in", "/out")
        step_id = step_repo.create_step(db, "run-1", "intake", "IntakeAgent")
        step_repo.update_step(
            db, step_id, status="passed",
            output_summary="2 files loaded", fingerprint="abc123"
        )
        steps = step_repo.get_steps_for_run(db, "run-1")
        assert steps[0]["status"] == "passed"
        assert steps[0]["fingerprint"] == "abc123"

    def test_multiple_attempts(self, db, run_repo, step_repo):
        run_repo.create_run(db, "run-1", "test", "/in", "/out")
        step_repo.create_step(db, "run-1", "extract", "ExtractAgent", attempt=1)
        step_repo.create_step(db, "run-1", "extract", "ExtractAgent", attempt=2)
        steps = step_repo.get_steps_for_run(db, "run-1")
        assert len(steps) == 2
        assert steps[0]["attempt"] == 1
        assert steps[1]["attempt"] == 2


# ---------------------------------------------------------------------------
# SpecResultRepository
# ---------------------------------------------------------------------------

class TestSpecResultRepository:
    def test_save_and_get_results(self, db, run_repo, step_repo, spec_repo):
        run_repo.create_run(db, "run-1", "test", "/in", "/out")
        step_id = step_repo.create_step(db, "run-1", "intake", "IntakeAgent")

        result = SpecResult(
            rule_id="intake_pre", passed=True,
            message="input_folder is set", suggested_fix=""
        )
        spec_repo.save_spec_result(db, step_id, "intake_pre", "pre", result)

        results = spec_repo.get_for_step(db, step_id)
        assert len(results) == 1
        assert results[0]["passed"] == 1
        assert results[0]["spec_type"] == "pre"

    def test_save_many(self, db, run_repo, step_repo, spec_repo):
        run_repo.create_run(db, "run-1", "test", "/in", "/out")
        step_id = step_repo.create_step(db, "run-1", "intake", "IntakeAgent")

        results = [
            SpecResult(rule_id="intake_pre", passed=True, message="OK"),
            SpecResult(rule_id="global_invariant", passed=True, message="OK"),
        ]
        spec_repo.save_many(db, step_id, "pre", results)

        saved = spec_repo.get_for_step(db, step_id)
        assert len(saved) == 2


# ---------------------------------------------------------------------------
# ContextSnapshotRepository
# ---------------------------------------------------------------------------

class TestContextSnapshotRepository:
    def test_save_before_after(self, db, run_repo, step_repo, ctx_repo):
        run_repo.create_run(db, "run-1", "test", "/in", "/out")
        step_id = step_repo.create_step(db, "run-1", "intake", "IntakeAgent")

        ctx_repo.save_snapshot(db, step_id, "before", {"input_folder": "/in"})
        ctx_repo.save_snapshot(
            db, step_id, "after",
            {"input_folder": "/in", "loaded_files": [{"filename": "a.txt"}]},
        )

        snaps = ctx_repo.get_for_step(db, step_id)
        assert len(snaps) == 2
        assert snaps[0]["snapshot_type"] == "before"
        assert snaps[1]["snapshot_type"] == "after"
        # data_json should be parsed back to dict
        assert "loaded_files" in snaps[1]["data_json"]


# ---------------------------------------------------------------------------
# TraceRepository
# ---------------------------------------------------------------------------

class TestTraceRepository:
    def test_save_and_get_trace(self, db, run_repo, step_repo, trace_repo):
        run_repo.create_run(db, "run-1", "test", "/in", "/out")
        step_id = step_repo.create_step(db, "run-1", "extract", "ExtractAgent")

        trace_repo.save_trace(
            db, step_id, "llm_call",
            input_data="Extract items from...",
            output_data='[{"title": "Task 1"}]',
            duration_ms=1200,
            tokens_used=450,
            model_name="gpt-4o",
        )

        traces = trace_repo.get_for_step(db, step_id)
        assert len(traces) == 1
        assert traces[0]["trace_type"] == "llm_call"
        assert traces[0]["tokens_used"] == 450

    def test_get_for_run(self, db, run_repo, step_repo, trace_repo):
        run_repo.create_run(db, "run-1", "test", "/in", "/out")
        step_id_1 = step_repo.create_step(db, "run-1", "intake", "IntakeAgent")
        step_id_2 = step_repo.create_step(db, "run-1", "extract", "ExtractAgent")

        trace_repo.save_trace(db, step_id_1, "file_read")
        trace_repo.save_trace(db, step_id_2, "llm_call")

        all_traces = trace_repo.get_for_run(db, "run-1")
        assert len(all_traces) == 2


# ---------------------------------------------------------------------------
# ItemRepository
# ---------------------------------------------------------------------------

class TestItemRepository:
    def test_save_and_get_items(self, db, run_repo, item_repo):
        run_repo.create_run(db, "run-1", "test", "/in", "/out")

        items = [
            {"title": "Implement login", "item_type": "task",
             "tags": ["auth"], "confidence": 0.9},
            {"title": "Fix CSV bug", "item_type": "bug",
             "tags": ["export", "csv"], "confidence": 0.85},
        ]
        ids = item_repo.save_items(db, "run-1", items)
        assert len(ids) == 2

        saved = item_repo.get_for_run(db, "run-1")
        assert len(saved) == 2
        assert saved[0]["title"] == "Implement login"
        assert saved[0]["tags"] == ["auth"]
        assert saved[1]["item_type"] == "bug"

    def test_get_all(self, db, run_repo, item_repo):
        run_repo.create_run(db, "run-1", "test", "/in", "/out")
        item_repo.save_items(db, "run-1", [{"title": "Item 1", "item_type": "note"}])
        all_items = item_repo.get_all(db)
        assert len(all_items) == 1


# ---------------------------------------------------------------------------
# SettingsRepository
# ---------------------------------------------------------------------------

class TestSettingsRepository:
    def test_set_and_get(self, db, settings_repo):
        settings_repo.set(db, "api_key", "sk-test-123")
        assert settings_repo.get(db, "api_key") == "sk-test-123"

    def test_upsert(self, db, settings_repo):
        settings_repo.set(db, "model", "gpt-4o")
        settings_repo.set(db, "model", "gpt-4o-mini")
        assert settings_repo.get(db, "model") == "gpt-4o-mini"

    def test_get_nonexistent(self, db, settings_repo):
        assert settings_repo.get(db, "nonexistent") is None

    def test_get_all(self, db, settings_repo):
        settings_repo.set(db, "key1", "val1")
        settings_repo.set(db, "key2", "val2")
        all_settings = settings_repo.get_all(db)
        assert all_settings == {"key1": "val1", "key2": "val2"}


# ---------------------------------------------------------------------------
# Foreign Key Constraints
# ---------------------------------------------------------------------------

class TestForeignKeys:
    def test_step_requires_valid_run(self, db, step_repo):
        with pytest.raises(sqlite3.IntegrityError):
            step_repo.create_step(db, "nonexistent-run", "intake", "Agent")

    def test_spec_result_requires_valid_step(self, db, spec_repo):
        result = SpecResult(rule_id="test", passed=True)
        with pytest.raises(sqlite3.IntegrityError):
            spec_repo.save_spec_result(db, "nonexistent-step", "test", "pre", result)

    def test_item_requires_valid_run(self, db, item_repo):
        with pytest.raises(sqlite3.IntegrityError):
            item_repo.save_items(db, "nonexistent-run", [{"title": "x"}])
