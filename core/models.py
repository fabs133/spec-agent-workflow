"""
Core data models for the Spec-Pattern Multi-Agent Workflow System.

These dataclasses define the shared vocabulary used across all modules:
- Context: shared state container passed through all steps
- SpecResult: outcome of evaluating a spec function
- StepAttempt: record of a single step execution
- RunRecord: complete record of a workflow run
"""

from __future__ import annotations

import uuid
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"


class SpecType(str, Enum):
    PRE = "pre"
    POST = "post"
    INVARIANT = "invariant"
    PROGRESS = "progress"


@dataclass
class SpecResult:
    """Result of evaluating a single spec function.

    Specs are pure functions that return this structured result.
    The suggested_fix field enables self-correction by agents.
    """
    rule_id: str
    passed: bool
    message: str = ""
    suggested_fix: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "passed": self.passed,
            "message": self.message,
            "suggested_fix": self.suggested_fix,
            "tags": self.tags,
        }


@dataclass
class Context:
    """Shared state container for a workflow run.

    Passed through all steps. Each step reads from and appends to this context.
    The orchestrator snapshots context before/after each step for traceability.

    Convention keys in data:
        input_folder: str - path to input files
        output_folder: str - path for output files
        loaded_files: List[Dict] - after intake (filename, content, size)
        extracted_items: List[Dict] - after extract (title, type, tags, description)
        written_files: List[str] - after write (output file paths)

    Convention keys in config:
        api_key: str - OpenAI API key
        model: str - model name (e.g. "gpt-4o")
        temperature: float - LLM temperature
    """
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    trace: List[Dict[str, Any]] = field(default_factory=list)
    budgets: Dict[str, int] = field(default_factory=lambda: {
        "max_retries_per_step": 3,
        "max_total_steps": 20,
    })
    config: Dict[str, Any] = field(default_factory=dict)

    def snapshot_data(self) -> Dict[str, Any]:
        """Return a deep-copy-safe JSON snapshot of data for DB storage."""
        return json.loads(json.dumps(self.data, default=str))

    def snapshot_artifacts(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self.artifacts, default=str))

    def add_trace(self, entry: Dict[str, Any]) -> None:
        """Append a trace entry with automatic timestamp."""
        entry.setdefault("timestamp", datetime.now().isoformat())
        self.trace.append(entry)


@dataclass
class StepAttempt:
    """Record of a single step execution attempt.

    Stores spec results, context snapshots, and fingerprint for loop detection.
    """
    step_id: str
    agent_id: str
    attempt: int
    status: StepStatus
    pre_results: List[SpecResult] = field(default_factory=list)
    post_results: List[SpecResult] = field(default_factory=list)
    invariant_results: List[SpecResult] = field(default_factory=list)
    context_before: Dict[str, Any] = field(default_factory=dict)
    context_after: Dict[str, Any] = field(default_factory=dict)
    fingerprint: str = ""
    error: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: str = ""

    @staticmethod
    def compute_fingerprint(step_id: str, context_data: Dict[str, Any],
                            failed_rule_ids: List[str]) -> str:
        """Compute a canonical fingerprint for loop detection.

        Same step + same effective input + same failures = identical fingerprint.
        Identical fingerprints are forbidden (prevents infinite retry loops).
        """
        canonical = json.dumps({
            "step_id": step_id,
            "data_keys": sorted(context_data.keys()),
            "failed_rules": sorted(failed_rule_ids),
        }, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


@dataclass
class RunRecord:
    """Complete record of a workflow execution."""
    run_id: str
    manifest_name: str
    status: RunStatus
    steps: List[StepAttempt] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: str = ""
    error: Optional[str] = None
    input_folder: str = ""
    output_folder: str = ""
    model_name: str = "gpt-4o"
