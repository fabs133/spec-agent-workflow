"""Orchestrator: the main execution engine.

Responsibilities:
1. Load manifest and build router
2. Execute steps in sequence following graph edges
3. Run pre/post/invariant specs at each step
4. Enforce retry budgets and detect loops
5. Snapshot context before/after each step for DB storage
6. Call on_step_update callback for frontend live visualization
7. Record everything to the database
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from core.agents import get_agent
from core.errors import BudgetExhaustedError, LoopDetectedError
from core.manifest import Manifest
from core.models import (
    Context,
    RunRecord,
    RunStatus,
    StepAttempt,
    StepStatus,
)
from core.router import Router
from core.specs import all_passed, evaluate_specs
from db.repository import (
    ContextSnapshotRepository,
    ItemRepository,
    RunRepository,
    SpecResultRepository,
    StepRepository,
    TraceRepository,
)

# Ensure agents are registered when orchestrator is imported
import agents  # noqa: F401


# Type for the frontend callback
StepCallback = Optional[Callable[[StepAttempt], None]]


class Orchestrator:
    """Executes a workflow defined by a manifest."""

    def __init__(self, manifest: Manifest, conn: sqlite3.Connection):
        self.manifest = manifest
        self.router = Router(manifest.edges)
        self.conn = conn

        # Repositories
        self.run_repo = RunRepository()
        self.step_repo = StepRepository()
        self.spec_repo = SpecResultRepository()
        self.ctx_repo = ContextSnapshotRepository()
        self.trace_repo = TraceRepository()
        self.item_repo = ItemRepository()

    async def run(
        self,
        context: Context,
        on_step_update: StepCallback = None,
    ) -> RunRecord:
        """Execute the full workflow.

        Args:
            context: Initial context with data and config filled in.
            on_step_update: Optional callback called after each step attempt.
                           Used by Streamlit for live visualization.
        """
        record = RunRecord(
            run_id=context.run_id,
            manifest_name=self.manifest.name,
            status=RunStatus.RUNNING,
            input_folder=context.data.get("input_folder", ""),
            output_folder=context.data.get("output_folder", ""),
            model_name=context.config.get("model", "gpt-4o"),
        )

        # Save run to DB
        self.run_repo.create_run(
            self.conn, context.run_id, self.manifest.name,
            record.input_folder, record.output_folder, record.model_name,
            config=context.config,
        )
        self.run_repo.update_run(
            self.conn, context.run_id,
            total_steps=len(self.manifest.steps),
        )

        # Track fingerprints for loop detection
        seen_fingerprints: Dict[str, set] = {}
        completed_steps = 0

        current_step_name = self.manifest.entry_step

        try:
            while current_step_name and current_step_name != "__end__":
                step_def = self.manifest.steps.get(current_step_name)
                if not step_def:
                    raise ValueError(f"Step '{current_step_name}' not found in manifest")

                # Budget check: total steps
                if completed_steps >= context.budgets.get("max_total_steps", 20):
                    raise BudgetExhaustedError("max_total_steps",
                                               context.budgets["max_total_steps"])

                step_passed = False
                max_attempts = step_def.retry.max_attempts

                for attempt in range(1, max_attempts + 1):
                    attempt_result = await self._execute_step_attempt(
                        context, step_def, attempt, seen_fingerprints
                    )
                    record.steps.append(attempt_result)

                    if on_step_update:
                        on_step_update(attempt_result)

                    if attempt_result.status == StepStatus.PASSED:
                        step_passed = True
                        completed_steps += 1
                        self.run_repo.update_run(
                            self.conn, context.run_id,
                            completed_steps=completed_steps,
                        )
                        break

                    # On failure, enrich context with error info for next attempt
                    if attempt < max_attempts:
                        context.data["_last_error"] = attempt_result.error
                        context.data["_last_failed_step"] = current_step_name
                        context.data["_retry_attempt"] = attempt + 1
                        await asyncio.sleep(step_def.retry.delay_seconds)

                # Route to next step
                next_step = self.router.next_step(current_step_name, step_passed)
                current_step_name = next_step

            # Success
            record.status = RunStatus.COMPLETED
            record.finished_at = datetime.now().isoformat()
            self.run_repo.update_run(
                self.conn, context.run_id, status="completed",
                completed_steps=completed_steps,
            )

            # Save extracted items to DB
            items = context.data.get("extracted_items", [])
            if items:
                self.item_repo.save_items(self.conn, context.run_id, items)

        except (BudgetExhaustedError, LoopDetectedError) as e:
            record.status = RunStatus.FAILED
            record.error = str(e)
            record.finished_at = datetime.now().isoformat()
            self.run_repo.update_run(
                self.conn, context.run_id,
                status="failed", error_message=str(e),
            )
        except Exception as e:
            record.status = RunStatus.FAILED
            record.error = str(e)
            record.finished_at = datetime.now().isoformat()
            self.run_repo.update_run(
                self.conn, context.run_id,
                status="failed", error_message=str(e),
            )

        return record

    async def _execute_step_attempt(
        self,
        context: Context,
        step_def,
        attempt: int,
        seen_fingerprints: Dict[str, set],
    ) -> StepAttempt:
        """Execute a single step attempt with full spec checking and tracing."""
        result = StepAttempt(
            step_id=step_def.name,
            agent_id=step_def.agent_name,
            attempt=attempt,
            status=StepStatus.RUNNING,
        )

        # Create step in DB
        step_db_id = self.step_repo.create_step(
            self.conn, context.run_id, step_def.name,
            step_def.agent_name, attempt,
        )

        try:
            # 1. Snapshot context BEFORE
            result.context_before = context.snapshot_data()
            self.ctx_repo.save_snapshot(
                self.conn, step_db_id, "before",
                result.context_before, context.snapshot_artifacts(),
            )

            # 2. Run PRE-SPECS
            if step_def.pre_specs:
                pre_results = evaluate_specs(step_def.pre_specs, context)
                result.pre_results = pre_results
                self.spec_repo.save_many(self.conn, step_db_id, "pre", pre_results)

                if not all_passed(pre_results):
                    failed = [r for r in pre_results if not r.passed]
                    error_msg = "; ".join(f"{r.rule_id}: {r.message}" for r in failed)
                    result.status = StepStatus.FAILED
                    result.error = f"Pre-spec failed: {error_msg}"
                    result.finished_at = datetime.now().isoformat()
                    self.step_repo.update_step(
                        self.conn, step_db_id,
                        status="failed", error_message=result.error,
                    )
                    return result

            # 3. Execute agent
            agent = get_agent(step_def.agent_name)
            trace_before_len = len(context.trace)
            context = await agent.execute(context)

            # 4. Save agent traces to DB
            new_traces = context.trace[trace_before_len:]
            for trace_entry in new_traces:
                self.trace_repo.save_trace(
                    self.conn, step_db_id,
                    trace_type=trace_entry.get("type", "unknown"),
                    input_data=trace_entry.get("prompt_preview", trace_entry.get("file", "")),
                    output_data=trace_entry.get("response_preview", ""),
                    duration_ms=trace_entry.get("duration_ms"),
                    tokens_used=trace_entry.get("tokens"),
                    model_name=trace_entry.get("model"),
                )

            # 5. Snapshot context AFTER
            result.context_after = context.snapshot_data()
            self.ctx_repo.save_snapshot(
                self.conn, step_db_id, "after",
                result.context_after, context.snapshot_artifacts(),
            )

            # 6. Run POST-SPECS
            if step_def.post_specs:
                post_results = evaluate_specs(step_def.post_specs, context)
                result.post_results = post_results
                self.spec_repo.save_many(self.conn, step_db_id, "post", post_results)

                if not all_passed(post_results):
                    failed = [r for r in post_results if not r.passed]
                    error_msg = "; ".join(f"{r.rule_id}: {r.message}" for r in failed)
                    result.status = StepStatus.FAILED
                    result.error = f"Post-spec failed: {error_msg}"

                    # Compute fingerprint for loop detection
                    failed_ids = [r.rule_id for r in failed]
                    fp = StepAttempt.compute_fingerprint(
                        step_def.name, context.snapshot_data(), failed_ids
                    )
                    result.fingerprint = fp

                    if step_def.name not in seen_fingerprints:
                        seen_fingerprints[step_def.name] = set()
                    if fp in seen_fingerprints[step_def.name]:
                        raise LoopDetectedError(step_def.name, fp)
                    seen_fingerprints[step_def.name].add(fp)

                    result.finished_at = datetime.now().isoformat()
                    self.step_repo.update_step(
                        self.conn, step_db_id,
                        status="failed", error_message=result.error,
                        fingerprint=fp,
                    )
                    return result

            # 7. Run INVARIANT-SPECS
            if step_def.invariant_specs:
                inv_results = evaluate_specs(step_def.invariant_specs, context)
                result.invariant_results = inv_results
                self.spec_repo.save_many(self.conn, step_db_id, "invariant", inv_results)

                if not all_passed(inv_results):
                    failed = [r for r in inv_results if not r.passed]
                    error_msg = "; ".join(f"{r.rule_id}: {r.message}" for r in failed)
                    result.status = StepStatus.FAILED
                    result.error = f"Invariant failed: {error_msg}"
                    result.finished_at = datetime.now().isoformat()
                    self.step_repo.update_step(
                        self.conn, step_db_id,
                        status="failed", error_message=result.error,
                    )
                    return result

            # 8. All passed
            result.status = StepStatus.PASSED
            result.finished_at = datetime.now().isoformat()

            # Build output summary
            summary_parts = []
            if step_def.post_specs:
                for r in result.post_results:
                    if r.passed:
                        summary_parts.append(r.message)
            output_summary = "; ".join(summary_parts) or "Step completed"

            self.step_repo.update_step(
                self.conn, step_db_id,
                status="passed", output_summary=output_summary,
            )
            return result

        except (LoopDetectedError, BudgetExhaustedError):
            raise
        except Exception as e:
            result.status = StepStatus.FAILED
            result.error = str(e)
            result.finished_at = datetime.now().isoformat()
            self.step_repo.update_step(
                self.conn, step_db_id,
                status="failed", error_message=str(e),
            )
            return result
