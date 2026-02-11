"""Tests for the orchestrator with mock agents.

Uses in-memory SQLite and mock agents to test the full workflow loop
without requiring an OpenAI API key.
"""

import asyncio
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from core.agents import BaseAgent, _AGENT_REGISTRY, register_agent
from core.manifest import Manifest
from core.models import Context, RunStatus, StepStatus
from core.orchestrator import Orchestrator

SCHEMA_PATH = Path(__file__).parent.parent / "db" / "schema.sql"


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Mock agents for testing
# ---------------------------------------------------------------------------

@register_agent("mock_intake")
class MockIntakeAgent(BaseAgent):
    async def execute(self, context: Context) -> Context:
        context.data["loaded_files"] = [
            {"filename": "test.txt", "content": "Hello world", "size": 11},
        ]
        context.add_trace({"type": "file_read", "agent": "mock_intake", "file": "test.txt"})
        return context


@register_agent("mock_extract")
class MockExtractAgent(BaseAgent):
    async def execute(self, context: Context) -> Context:
        context.data["extracted_items"] = [
            {
                "title": "Test task",
                "item_type": "task",
                "description": "A test task.",
                "tags": ["test"],
                "source_file": "test.txt",
                "confidence": 0.95,
            },
        ]
        context.add_trace({"type": "llm_call", "agent": "mock_extract", "tokens": 100})
        return context


@register_agent("mock_write")
class MockWriteAgent(BaseAgent):
    async def execute(self, context: Context) -> Context:
        context.data["written_files"] = ["/tmp/output/results.json"]
        context.add_trace({"type": "file_write", "agent": "mock_write", "file": "results.json"})
        return context


@register_agent("mock_failing")
class MockFailingAgent(BaseAgent):
    """Agent that never produces valid output (post-spec will fail)."""
    async def execute(self, context: Context) -> Context:
        # Deliberately don't set extracted_items
        return context


@register_agent("mock_error")
class MockErrorAgent(BaseAgent):
    """Agent that raises an exception."""
    async def execute(self, context: Context) -> Context:
        raise RuntimeError("Agent crashed!")


# ---------------------------------------------------------------------------
# Test manifests
# ---------------------------------------------------------------------------

HAPPY_PATH_MANIFEST = {
    "name": "test_happy",
    "entry_step": "intake",
    "steps": {
        "intake": {
            "agent": "mock_intake",
            "specs": {"pre": ["intake_pre"], "post": ["intake_post"], "invariant": ["global_invariant"]},
            "retry": {"max_attempts": 1},
        },
        "extract": {
            "agent": "mock_extract",
            "specs": {"pre": ["extract_pre"], "post": ["extract_post"]},
            "retry": {"max_attempts": 1},
        },
        "write": {
            "agent": "mock_write",
            "specs": {"pre": ["write_pre"], "post": ["write_post"]},
            "retry": {"max_attempts": 1},
        },
    },
    "edges": [
        {"from": "intake", "to": "extract", "condition": "on_pass"},
        {"from": "extract", "to": "write", "condition": "on_pass"},
    ],
}

FAILING_EXTRACT_MANIFEST = {
    "name": "test_failing",
    "entry_step": "intake",
    "steps": {
        "intake": {
            "agent": "mock_intake",
            "specs": {"pre": ["intake_pre"], "post": ["intake_post"]},
            "retry": {"max_attempts": 1},
        },
        "extract": {
            "agent": "mock_failing",
            "specs": {"pre": ["extract_pre"], "post": ["extract_post"]},
            "retry": {"max_attempts": 2},
        },
    },
    "edges": [
        {"from": "intake", "to": "extract", "condition": "on_pass"},
    ],
}

ERROR_AGENT_MANIFEST = {
    "name": "test_error",
    "entry_step": "step_one",
    "steps": {
        "step_one": {
            "agent": "mock_error",
            "specs": {"pre": ["intake_pre"]},
            "retry": {"max_attempts": 1},
        },
    },
    "edges": [],
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestOrchestratorHappyPath:
    def test_full_workflow_completes(self, db):
        manifest = Manifest.from_dict(HAPPY_PATH_MANIFEST)
        orch = Orchestrator(manifest, db)
        context = Context(
            data={"input_folder": "/tmp/input", "output_folder": "/tmp/output"},
            config={"api_key": "test-key", "model": "gpt-4o"},
        )

        record = asyncio.run(orch.run(context))

        assert record.status == RunStatus.COMPLETED
        assert len(record.steps) == 3
        assert all(s.status == StepStatus.PASSED for s in record.steps)

    def test_run_saved_to_db(self, db):
        manifest = Manifest.from_dict(HAPPY_PATH_MANIFEST)
        orch = Orchestrator(manifest, db)
        context = Context(
            data={"input_folder": "/tmp/input", "output_folder": "/tmp/output"},
            config={"api_key": "test-key"},
        )

        record = asyncio.run(orch.run(context))

        # Check workflow_runs
        run = orch.run_repo.get_run(db, context.run_id)
        assert run is not None
        assert run["status"] == "completed"

        # Check step_executions
        steps = orch.step_repo.get_steps_for_run(db, context.run_id)
        assert len(steps) == 3

        # Check spec_results
        for step in steps:
            specs = orch.spec_repo.get_for_step(db, step["id"])
            assert len(specs) > 0  # At least pre + post

        # Check context_snapshots
        for step in steps:
            snaps = orch.ctx_repo.get_for_step(db, step["id"])
            assert len(snaps) == 2  # before + after

        # Check extracted_items
        items = orch.item_repo.get_for_run(db, context.run_id)
        assert len(items) == 1
        assert items[0]["title"] == "Test task"

    def test_callback_called_for_each_step(self, db):
        manifest = Manifest.from_dict(HAPPY_PATH_MANIFEST)
        orch = Orchestrator(manifest, db)
        context = Context(
            data={"input_folder": "/tmp/input", "output_folder": "/tmp/output"},
            config={"api_key": "test-key"},
        )

        callbacks = []
        record = asyncio.run(orch.run(context, on_step_update=callbacks.append))

        assert len(callbacks) == 3
        assert callbacks[0].step_id == "intake"
        assert callbacks[1].step_id == "extract"
        assert callbacks[2].step_id == "write"


class TestOrchestratorFailures:
    def test_pre_spec_failure_skips_agent(self, db):
        """If pre_spec fails, agent should not execute."""
        manifest = Manifest.from_dict({
            "name": "test_pre_fail",
            "entry_step": "extract",
            "steps": {
                "extract": {
                    "agent": "mock_extract",
                    "specs": {"pre": ["extract_pre"]},  # Will fail: no loaded_files
                    "retry": {"max_attempts": 1},
                },
            },
            "edges": [],
        })
        orch = Orchestrator(manifest, db)
        context = Context(
            data={"input_folder": "/tmp/input"},
            config={},  # No api_key either
        )

        record = asyncio.run(orch.run(context))

        # extract_pre should fail (no loaded_files)
        assert record.steps[0].status == StepStatus.FAILED
        assert "Pre-spec failed" in record.steps[0].error

    def test_post_spec_failure_retries(self, db):
        """If post_spec fails, step should be retried."""
        manifest = Manifest.from_dict(FAILING_EXTRACT_MANIFEST)
        orch = Orchestrator(manifest, db)
        context = Context(
            data={"input_folder": "/tmp/input", "output_folder": "/tmp/output"},
            config={"api_key": "test-key"},
        )

        record = asyncio.run(orch.run(context))

        # intake passes, extract fails twice (mock_failing doesn't set extracted_items)
        extract_attempts = [s for s in record.steps if s.step_id == "extract"]
        assert len(extract_attempts) == 2
        assert all(s.status == StepStatus.FAILED for s in extract_attempts)

    def test_agent_exception_caught(self, db):
        """Agent exceptions should be caught and recorded."""
        manifest = Manifest.from_dict(ERROR_AGENT_MANIFEST)
        orch = Orchestrator(manifest, db)
        context = Context(
            data={"input_folder": "/tmp/input"},
            config={"api_key": "test-key"},
        )

        record = asyncio.run(orch.run(context))

        assert record.steps[0].status == StepStatus.FAILED
        assert "Agent crashed" in record.steps[0].error


class TestOrchestratorBudgets:
    def test_total_steps_budget(self, db):
        manifest = Manifest.from_dict(HAPPY_PATH_MANIFEST)
        orch = Orchestrator(manifest, db)
        context = Context(
            data={"input_folder": "/tmp/input", "output_folder": "/tmp/output"},
            config={"api_key": "test-key"},
            budgets={"max_total_steps": 1, "max_retries_per_step": 3},
        )

        record = asyncio.run(orch.run(context))

        # Should complete intake (1 step) then hit budget on extract
        assert record.status == RunStatus.FAILED
        assert "budget" in record.error.lower() or "Budget" in record.error


class TestOrchestratorTracing:
    def test_agent_traces_saved(self, db):
        manifest = Manifest.from_dict(HAPPY_PATH_MANIFEST)
        orch = Orchestrator(manifest, db)
        context = Context(
            data={"input_folder": "/tmp/input", "output_folder": "/tmp/output"},
            config={"api_key": "test-key"},
        )

        asyncio.run(orch.run(context))

        # Check that traces were saved
        steps = orch.step_repo.get_steps_for_run(db, context.run_id)
        all_traces = []
        for step in steps:
            traces = orch.trace_repo.get_for_step(db, step["id"])
            all_traces.extend(traces)

        assert len(all_traces) >= 3  # At least one trace per step
        trace_types = {t["trace_type"] for t in all_traces}
        assert "file_read" in trace_types
        assert "llm_call" in trace_types
        assert "file_write" in trace_types
