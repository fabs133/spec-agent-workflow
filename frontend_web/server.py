"""Standalone HTTP server with JSON API for the Spec-Agent Workflow System.

Uses only Python standard library (http.server, json, threading, sqlite3).
Serves static files from frontend_web/static/ and exposes a JSON API.
"""

from __future__ import annotations

import asyncio
import json
import mimetypes
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

# Project imports
from core.manifest import Manifest
from core.models import Context, StepStatus
from core.orchestrator import Orchestrator
from db.connection import get_connection, init_db
from db.repository import (
    ContextSnapshotRepository,
    ItemRepository,
    RunRepository,
    SettingsRepository,
    SpecResultRepository,
    StepRepository,
    TraceRepository,
)

PROJECT_ROOT = Path(__file__).parent.parent
STATIC_DIR = Path(__file__).parent / "static"
MANIFEST_PATH = PROJECT_ROOT / "manifests" / "text_extraction.json"

# In-memory workflow execution state
_running_workflows: Dict[str, Dict[str, Any]] = {}
_workflow_lock = threading.Lock()


class APIHandler(BaseHTTPRequestHandler):
    """Handle JSON API requests and serve static files."""

    def log_message(self, format, *args):
        """Suppress default request logging."""
        pass

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        # API routes
        if path == "/api/stats":
            self._handle_stats()
        elif path == "/api/settings":
            self._handle_get_settings()
        elif path == "/api/runs":
            limit = int(qs.get("limit", ["50"])[0])
            self._handle_list_runs(limit)
        elif (m := re.match(r"^/api/runs/([^/]+)/steps$", path)):
            self._handle_run_steps(m.group(1))
        elif (m := re.match(r"^/api/runs/([^/]+)/items$", path)):
            self._handle_run_items(m.group(1))
        elif (m := re.match(r"^/api/runs/([^/]+)$", path)):
            self._handle_get_run(m.group(1))
        elif path == "/api/items":
            self._handle_list_items(qs)
        elif path == "/api/manifest":
            self._handle_manifest()
        elif path == "/api/manifest/raw":
            self._handle_manifest_raw()
        elif path == "/api/input-files":
            self._handle_input_files(qs)
        elif path == "/api/workflow/status":
            run_id = qs.get("run_id", [None])[0]
            self._handle_workflow_status(run_id)
        elif path == "/api/specs":
            self._handle_specs()
        elif path == "/api/step-detail":
            step_id = qs.get("step_id", [None])[0]
            self._handle_step_detail(step_id)
        else:
            self._serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()

        if path == "/api/settings":
            self._handle_save_settings(body)
        elif path == "/api/workflow/run":
            self._handle_start_workflow(body)
        else:
            self._json_response({"error": "Not found"}, 404)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _read_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw)

    def _json_response(self, data: Any, status: int = 200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, path: str):
        if path == "/" or path == "":
            path = "/index.html"

        file_path = STATIC_DIR / path.lstrip("/")

        # Security: prevent path traversal
        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(STATIC_DIR.resolve())):
                self._json_response({"error": "Forbidden"}, 403)
                return
        except Exception:
            self._json_response({"error": "Forbidden"}, 403)
            return

        if not file_path.exists() or not file_path.is_file():
            # SPA fallback: serve index.html for unmatched routes
            file_path = STATIC_DIR / "index.html"
            if not file_path.exists():
                self._json_response({"error": "Not found"}, 404)
                return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            mime_type = "application/octet-stream"

        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    # ------------------------------------------------------------------
    # API Handlers
    # ------------------------------------------------------------------

    def _handle_stats(self):
        conn = get_connection()
        run_repo = RunRepository()
        item_repo = ItemRepository()
        runs = run_repo.list_runs(conn, limit=5000)
        items = item_repo.get_all(conn, limit=50000)
        conn.close()

        self._json_response({
            "total_runs": len(runs),
            "completed": sum(1 for r in runs if r["status"] == "completed"),
            "failed": sum(1 for r in runs if r["status"] == "failed"),
            "total_items": len(items),
        })

    def _handle_get_settings(self):
        conn = get_connection()
        repo = SettingsRepository()
        settings = repo.get_all(conn)
        conn.close()
        self._json_response(settings)

    def _handle_save_settings(self, body: Dict[str, Any]):
        conn = get_connection()
        repo = SettingsRepository()
        for key, value in body.items():
            repo.set(conn, key, str(value))
        conn.close()
        self._json_response({"status": "ok"})

    def _handle_list_runs(self, limit: int):
        conn = get_connection()
        repo = RunRepository()
        runs = repo.list_runs(conn, limit=limit)
        conn.close()
        self._json_response(runs)

    def _handle_get_run(self, run_id: str):
        conn = get_connection()
        run_repo = RunRepository()
        step_repo = StepRepository()
        spec_repo = SpecResultRepository()
        ctx_repo = ContextSnapshotRepository()
        trace_repo = TraceRepository()
        item_repo = ItemRepository()

        run = run_repo.get_run(conn, run_id)
        if not run:
            conn.close()
            self._json_response({"error": "Run not found"}, 404)
            return

        steps = step_repo.get_steps_for_run(conn, run_id)
        items = item_repo.get_for_run(conn, run_id)

        # Enrich steps with specs, traces, snapshots
        enriched_steps = []
        for step in steps:
            step_id = step["id"]
            specs = spec_repo.get_for_step(conn, step_id)
            traces = trace_repo.get_for_step(conn, step_id)
            snapshots = ctx_repo.get_for_step(conn, step_id)

            before = None
            after = None
            for snap in snapshots:
                if snap["snapshot_type"] == "before":
                    before = snap["data_json"]
                elif snap["snapshot_type"] == "after":
                    after = snap["data_json"]

            enriched_steps.append({
                **step,
                "specs": specs,
                "traces": traces,
                "context_before": before,
                "context_after": after,
            })

        conn.close()
        self._json_response({
            "run": run,
            "steps": enriched_steps,
            "items": items,
        })

    def _handle_run_steps(self, run_id: str):
        conn = get_connection()
        repo = StepRepository()
        steps = repo.get_steps_for_run(conn, run_id)
        conn.close()
        self._json_response(steps)

    def _handle_run_items(self, run_id: str):
        conn = get_connection()
        repo = ItemRepository()
        items = repo.get_for_run(conn, run_id)
        conn.close()
        self._json_response(items)

    def _handle_list_items(self, qs: Dict):
        conn = get_connection()
        repo = ItemRepository()
        limit = int(qs.get("limit", ["500"])[0])
        items = repo.get_all(conn, limit=limit)
        conn.close()
        self._json_response(items)

    def _handle_manifest(self):
        try:
            manifest = Manifest.from_file(MANIFEST_PATH)
            steps = {}
            for name, s in manifest.steps.items():
                steps[name] = {
                    "agent_name": s.agent_name,
                    "pre_specs": s.pre_specs,
                    "post_specs": s.post_specs,
                    "invariant_specs": s.invariant_specs,
                    "retry": {
                        "max_attempts": s.retry.max_attempts,
                        "delay_seconds": s.retry.delay_seconds,
                    },
                }
            edges = [
                {"from": e.from_step, "to": e.to_step, "condition": e.condition}
                for e in manifest.edges
            ]
            self._json_response({
                "name": manifest.name,
                "description": manifest.description,
                "version": manifest.version,
                "entry_step": manifest.entry_step,
                "steps": steps,
                "edges": edges,
                "defaults": manifest.defaults,
                "budgets": manifest.budgets,
            })
        except Exception as e:
            self._json_response({"error": str(e)}, 500)

    def _handle_manifest_raw(self):
        try:
            raw = MANIFEST_PATH.read_text(encoding="utf-8")
            self._json_response({"content": raw, "filename": MANIFEST_PATH.name})
        except Exception as e:
            self._json_response({"error": str(e)}, 500)

    def _handle_input_files(self, qs: Dict):
        conn = get_connection()
        repo = SettingsRepository()
        folder = qs.get("folder", [None])[0]
        if not folder:
            folder = repo.get(conn, "default_input_folder") or str(
                PROJECT_ROOT / "data" / "input"
            )
        conn.close()

        path = Path(folder)
        if not path.exists():
            self._json_response({"files": [], "error": f"Folder not found: {folder}"})
            return

        files = []
        for f in sorted(path.iterdir()):
            if f.is_file() and f.suffix.lower() in (".txt", ".md"):
                files.append({"name": f.name, "size": f.stat().st_size})

        self._json_response({"files": files, "folder": str(folder)})

    def _handle_start_workflow(self, body: Dict[str, Any]):
        conn = get_connection()
        repo = SettingsRepository()

        api_key = body.get("api_key") or repo.get(conn, "openai_api_key") or ""
        model = body.get("model") or repo.get(conn, "default_model") or "gpt-4o"
        input_folder = body.get("input_folder") or repo.get(
            conn, "default_input_folder"
        ) or str(PROJECT_ROOT / "data" / "input")
        output_folder = body.get("output_folder") or repo.get(
            conn, "default_output_folder"
        ) or str(PROJECT_ROOT / "data" / "output")
        conn.close()

        if not api_key:
            self._json_response({"error": "No API key configured"}, 400)
            return

        context = Context(
            data={
                "input_folder": input_folder,
                "output_folder": output_folder,
            },
            config={
                "api_key": api_key,
                "model": model,
                "temperature": 0.3,
            },
        )
        run_id = context.run_id

        # Load manifest
        try:
            manifest = Manifest.from_file(MANIFEST_PATH)
        except Exception as e:
            self._json_response({"error": f"Manifest error: {e}"}, 500)
            return

        # Get step order
        from core.router import Router
        router = Router(manifest.edges)
        step_names = [manifest.entry_step]
        current = manifest.entry_step
        visited = {current}
        while True:
            next_s = router.next_step(current, step_passed=True)
            if not next_s or next_s == "__end__" or next_s in visited:
                break
            step_names.append(next_s)
            visited.add(next_s)
            current = next_s

        # Initialize workflow state
        with _workflow_lock:
            _running_workflows[run_id] = {
                "status": "running",
                "step_names": step_names,
                "step_statuses": {s: "pending" for s in step_names},
                "step_results": [],
                "error": None,
                "items_count": 0,
            }

        def run_workflow():
            wf_conn = get_connection()
            orch = Orchestrator(manifest, wf_conn)

            def on_step_update(attempt):
                with _workflow_lock:
                    wf = _running_workflows.get(run_id)
                    if wf:
                        wf["step_statuses"][attempt.step_id] = attempt.status.value
                        wf["step_results"].append({
                            "step_id": attempt.step_id,
                            "attempt": attempt.attempt,
                            "status": attempt.status.value,
                            "error": attempt.error,
                            "pre_results": [r.to_dict() for r in attempt.pre_results],
                            "post_results": [r.to_dict() for r in attempt.post_results],
                            "invariant_results": [r.to_dict() for r in attempt.invariant_results],
                        })

            try:
                record = asyncio.run(orch.run(context, on_step_update=on_step_update))
                with _workflow_lock:
                    wf = _running_workflows.get(run_id)
                    if wf:
                        wf["status"] = record.status.value
                        wf["error"] = record.error
                        wf["items_count"] = len(
                            context.data.get("extracted_items", [])
                        )
            except Exception as e:
                with _workflow_lock:
                    wf = _running_workflows.get(run_id)
                    if wf:
                        wf["status"] = "failed"
                        wf["error"] = str(e)
            finally:
                wf_conn.close()

        t = threading.Thread(target=run_workflow, daemon=True)
        t.start()

        self._json_response({"run_id": run_id, "status": "started"})

    def _handle_workflow_status(self, run_id: Optional[str]):
        if not run_id:
            self._json_response({"error": "run_id required"}, 400)
            return

        with _workflow_lock:
            wf = _running_workflows.get(run_id)

        if not wf:
            self._json_response({"error": "Workflow not found"}, 404)
            return

        self._json_response(wf)

    def _handle_specs(self):
        from core.specs import _SPEC_REGISTRY
        import inspect

        specs = {}
        for name, func in _SPEC_REGISTRY.items():
            try:
                source = inspect.getsource(func)
            except Exception:
                source = ""
            specs[name] = {
                "name": name,
                "doc": (func.__doc__ or "").strip(),
                "source": source,
            }
        self._json_response(specs)

    def _handle_step_detail(self, step_id: Optional[str]):
        if not step_id:
            self._json_response({"error": "step_id required"}, 400)
            return

        conn = get_connection()
        spec_repo = SpecResultRepository()
        trace_repo = TraceRepository()
        ctx_repo = ContextSnapshotRepository()

        specs = spec_repo.get_for_step(conn, step_id)
        traces = trace_repo.get_for_step(conn, step_id)
        snapshots = ctx_repo.get_for_step(conn, step_id)

        before = after = None
        for snap in snapshots:
            if snap["snapshot_type"] == "before":
                before = snap["data_json"]
            elif snap["snapshot_type"] == "after":
                after = snap["data_json"]

        conn.close()
        self._json_response({
            "specs": specs,
            "traces": traces,
            "context_before": before,
            "context_after": after,
        })


def start_server(port: int = 8501):
    """Start the HTTP server."""
    init_db()
    server = HTTPServer(("127.0.0.1", port), APIHandler)
    print(f"Spec-Agent Workflow running at http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
