"""Repository pattern for database access.

Each repository handles CRUD for one table family.
All methods take a sqlite3.Connection parameter for testability.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.models import SpecResult, SpecType


def _now() -> str:
    return datetime.now().isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# RunRepository
# ---------------------------------------------------------------------------

class RunRepository:
    """CRUD for workflow_runs table."""

    def create_run(
        self,
        conn: sqlite3.Connection,
        run_id: str,
        manifest_name: str,
        input_folder: str,
        output_folder: str,
        model_name: str = "gpt-4o",
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        conn.execute(
            """INSERT INTO workflow_runs
               (id, manifest_name, status, started_at, input_folder, output_folder,
                model_name, config_json)
               VALUES (?, ?, 'running', ?, ?, ?, ?, ?)""",
            (run_id, manifest_name, _now(), input_folder, output_folder,
             model_name, json.dumps(config or {})),
        )
        conn.commit()
        return run_id

    def update_run(
        self,
        conn: sqlite3.Connection,
        run_id: str,
        status: Optional[str] = None,
        completed_steps: Optional[int] = None,
        total_steps: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        updates = []
        params: list = []
        if status:
            updates.append("status = ?")
            params.append(status)
        if completed_steps is not None:
            updates.append("completed_steps = ?")
            params.append(completed_steps)
        if total_steps is not None:
            updates.append("total_steps = ?")
            params.append(total_steps)
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        if status in ("completed", "failed"):
            updates.append("finished_at = ?")
            params.append(_now())

        if updates:
            params.append(run_id)
            conn.execute(
                f"UPDATE workflow_runs SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            conn.commit()

    def get_run(self, conn: sqlite3.Connection, run_id: str) -> Optional[Dict[str, Any]]:
        row = conn.execute(
            "SELECT * FROM workflow_runs WHERE id = ?", (run_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_runs(self, conn: sqlite3.Connection, limit: int = 50) -> List[Dict[str, Any]]:
        rows = conn.execute(
            "SELECT * FROM workflow_runs ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# StepRepository
# ---------------------------------------------------------------------------

class StepRepository:
    """CRUD for step_executions table."""

    def create_step(
        self,
        conn: sqlite3.Connection,
        run_id: str,
        step_name: str,
        agent_name: str,
        attempt: int = 1,
    ) -> str:
        step_id = _uuid()
        conn.execute(
            """INSERT INTO step_executions
               (id, run_id, step_name, agent_name, attempt, status, started_at)
               VALUES (?, ?, ?, ?, ?, 'running', ?)""",
            (step_id, run_id, step_name, agent_name, attempt, _now()),
        )
        conn.commit()
        return step_id

    def update_step(
        self,
        conn: sqlite3.Connection,
        step_id: str,
        status: Optional[str] = None,
        error_message: Optional[str] = None,
        output_summary: Optional[str] = None,
        fingerprint: Optional[str] = None,
    ) -> None:
        updates = []
        params: list = []
        if status:
            updates.append("status = ?")
            params.append(status)
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        if output_summary is not None:
            updates.append("output_summary = ?")
            params.append(output_summary)
        if fingerprint is not None:
            updates.append("fingerprint = ?")
            params.append(fingerprint)
        if status in ("passed", "failed"):
            updates.append("finished_at = ?")
            params.append(_now())

        if updates:
            params.append(step_id)
            conn.execute(
                f"UPDATE step_executions SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            conn.commit()

    def get_steps_for_run(
        self, conn: sqlite3.Connection, run_id: str
    ) -> List[Dict[str, Any]]:
        rows = conn.execute(
            """SELECT * FROM step_executions WHERE run_id = ?
               ORDER BY started_at ASC""",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# SpecResultRepository
# ---------------------------------------------------------------------------

class SpecResultRepository:
    """CRUD for spec_results table."""

    def save_spec_result(
        self,
        conn: sqlite3.Connection,
        step_execution_id: str,
        spec_name: str,
        spec_type: str,
        result: SpecResult,
    ) -> str:
        result_id = _uuid()
        conn.execute(
            """INSERT INTO spec_results
               (id, step_execution_id, spec_name, spec_type, passed, detail,
                suggested_fix, evaluated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (result_id, step_execution_id, spec_name, spec_type,
             1 if result.passed else 0, result.message,
             result.suggested_fix, _now()),
        )
        conn.commit()
        return result_id

    def save_many(
        self,
        conn: sqlite3.Connection,
        step_execution_id: str,
        spec_type: str,
        results: List[SpecResult],
    ) -> None:
        now = _now()
        rows = [
            (_uuid(), step_execution_id, r.rule_id, spec_type,
             1 if r.passed else 0, r.message, r.suggested_fix, now)
            for r in results
        ]
        conn.executemany(
            """INSERT INTO spec_results
               (id, step_execution_id, spec_name, spec_type, passed, detail,
                suggested_fix, evaluated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()

    def get_for_step(
        self, conn: sqlite3.Connection, step_execution_id: str
    ) -> List[Dict[str, Any]]:
        rows = conn.execute(
            """SELECT * FROM spec_results WHERE step_execution_id = ?
               ORDER BY evaluated_at ASC""",
            (step_execution_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# ContextSnapshotRepository
# ---------------------------------------------------------------------------

class ContextSnapshotRepository:
    """CRUD for context_snapshots table."""

    def save_snapshot(
        self,
        conn: sqlite3.Connection,
        step_execution_id: str,
        snapshot_type: str,
        data: Dict[str, Any],
        artifacts: Optional[Dict[str, Any]] = None,
    ) -> str:
        snap_id = _uuid()
        conn.execute(
            """INSERT INTO context_snapshots
               (id, step_execution_id, snapshot_type, data_json, artifacts_json, captured_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (snap_id, step_execution_id, snapshot_type,
             json.dumps(data, default=str),
             json.dumps(artifacts or {}, default=str),
             _now()),
        )
        conn.commit()
        return snap_id

    def get_for_step(
        self, conn: sqlite3.Connection, step_execution_id: str
    ) -> List[Dict[str, Any]]:
        rows = conn.execute(
            """SELECT * FROM context_snapshots WHERE step_execution_id = ?
               ORDER BY captured_at ASC""",
            (step_execution_id,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["data_json"] = json.loads(d["data_json"]) if d["data_json"] else {}
            d["artifacts_json"] = json.loads(d["artifacts_json"]) if d["artifacts_json"] else {}
            result.append(d)
        return result


# ---------------------------------------------------------------------------
# TraceRepository
# ---------------------------------------------------------------------------

class TraceRepository:
    """CRUD for agent_traces table."""

    def save_trace(
        self,
        conn: sqlite3.Connection,
        step_execution_id: str,
        trace_type: str,
        input_data: Optional[str] = None,
        output_data: Optional[str] = None,
        duration_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
        model_name: Optional[str] = None,
    ) -> str:
        trace_id = _uuid()
        conn.execute(
            """INSERT INTO agent_traces
               (id, step_execution_id, trace_type, timestamp, input_data,
                output_data, duration_ms, tokens_used, model_name)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (trace_id, step_execution_id, trace_type, _now(),
             input_data, output_data, duration_ms, tokens_used, model_name),
        )
        conn.commit()
        return trace_id

    def get_for_step(
        self, conn: sqlite3.Connection, step_execution_id: str
    ) -> List[Dict[str, Any]]:
        rows = conn.execute(
            """SELECT * FROM agent_traces WHERE step_execution_id = ?
               ORDER BY timestamp ASC""",
            (step_execution_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_for_run(
        self, conn: sqlite3.Connection, run_id: str
    ) -> List[Dict[str, Any]]:
        rows = conn.execute(
            """SELECT t.* FROM agent_traces t
               JOIN step_executions s ON t.step_execution_id = s.id
               WHERE s.run_id = ?
               ORDER BY t.timestamp ASC""",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# ItemRepository
# ---------------------------------------------------------------------------

class ItemRepository:
    """CRUD for extracted_items table."""

    def save_items(
        self,
        conn: sqlite3.Connection,
        run_id: str,
        items: List[Dict[str, Any]],
    ) -> List[str]:
        ids = []
        now = _now()
        for item in items:
            item_id = _uuid()
            ids.append(item_id)
            conn.execute(
                """INSERT INTO extracted_items
                   (id, run_id, title, item_type, description, tags,
                    source_file, confidence, raw_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (item_id, run_id, item.get("title", ""),
                 item.get("item_type", "note"),
                 item.get("description", ""),
                 json.dumps(item.get("tags", [])),
                 item.get("source_file", ""),
                 item.get("confidence", 0.8),
                 json.dumps(item, default=str),
                 now),
            )
        conn.commit()
        return ids

    def get_for_run(
        self, conn: sqlite3.Connection, run_id: str
    ) -> List[Dict[str, Any]]:
        rows = conn.execute(
            "SELECT * FROM extracted_items WHERE run_id = ? ORDER BY created_at ASC",
            (run_id,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["tags"] = json.loads(d["tags"]) if d["tags"] else []
            result.append(d)
        return result

    def get_all(
        self, conn: sqlite3.Connection, limit: int = 100
    ) -> List[Dict[str, Any]]:
        rows = conn.execute(
            "SELECT * FROM extracted_items ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["tags"] = json.loads(d["tags"]) if d["tags"] else []
            result.append(d)
        return result


# ---------------------------------------------------------------------------
# SettingsRepository
# ---------------------------------------------------------------------------

class SettingsRepository:
    """CRUD for app_settings table."""

    def get(self, conn: sqlite3.Connection, key: str) -> Optional[str]:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def set(self, conn: sqlite3.Connection, key: str, value: str) -> None:
        conn.execute(
            """INSERT INTO app_settings (key, value, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?""",
            (key, value, _now(), value, _now()),
        )
        conn.commit()

    def get_all(self, conn: sqlite3.Connection) -> Dict[str, str]:
        rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
        return {r["key"]: r["value"] for r in rows}
