Architecture
============

Overview
--------

The Spec-Pattern Multi-Agent Architecture separates concerns into distinct
components, each with a single responsibility:

.. list-table::
   :header-rows: 1
   :widths: 20 40 20

   * - Component
     - Role
     - Purity
   * - **Context**
     - Shared state container passed through all steps
     - Data only
   * - **Specs**
     - Pure validation functions (pre/post/invariant)
     - Pure (no IO)
   * - **Agents**
     - Execute tasks (file IO, LLM calls)
     - IO allowed
   * - **Router**
     - Choose next step based on spec outcomes
     - Logic only
   * - **Manifest**
     - Define workflow graph as YAML data
     - Data (YAML)
   * - **Orchestrator**
     - Execute steps, enforce budgets, record traces
     - Coordination
   * - **Database**
     - Store execution traces for visualization
     - Persistence

Core Design Principles
----------------------

1. **Graph as Data**: The workflow is defined in YAML (the manifest), not in Python code.
   Changing the workflow means editing a YAML file, not rewriting code.

2. **Specs are Pure**: Specification functions have no IO, no side effects, and are
   deterministic. This makes them trivially testable (29 tests, zero mocking needed).

3. **Agents Don't Control Flow**: Agents transform context into output. They never
   decide what runs next -- that is the router's job based on spec outcomes.

4. **No Identical Retries**: After a failure, the system enriches the context with error
   information before retrying. If the same fingerprint repeats, the retry is blocked
   (loop detection).

5. **Full Traceability**: Every step execution records context snapshots (before/after),
   spec results, and agent traces in SQLite.

Orchestrator Loop
-----------------

The orchestrator executes this loop for each step:

1. Check global invariants on context
2. Run **pre-specs** -- if fail, skip agent
3. Snapshot context (BEFORE)
4. Execute **agent**
5. Snapshot context (AFTER)
6. Run **post-specs** -- if fail, retry with enriched context
7. Run **invariant-specs** -- if fail, halt workflow
8. Compute failure fingerprint for loop detection
9. Save everything to SQLite
10. Notify frontend via callback
11. Use **router** to find next step from edges

Loop Prevention
---------------

After each failure, the system computes a hash (fingerprint) of:

- Step name
- Context data keys
- Failed rule IDs (sorted)

If the same fingerprint repeats for the same step, the system raises a
``LoopDetectedError`` instead of retrying identically. Retries are only
allowed when the "situation changed" (new data, different failing rules).

Database Schema
---------------

The SQLite database has 7 tables:

- ``workflow_runs`` -- Top-level run records
- ``step_executions`` -- One row per step attempt (including retries)
- ``spec_results`` -- Individual spec check outcomes
- ``context_snapshots`` -- Full context before/after each step
- ``agent_traces`` -- Detailed agent action log (LLM calls, file ops)
- ``extracted_items`` -- The actual workflow output
- ``app_settings`` -- Persisted configuration

Key relationships::

    workflow_runs  1 --< N  step_executions  1 --< N  spec_results
                                             1 --< N  context_snapshots
                                             1 --< N  agent_traces
    workflow_runs  1 --< N  extracted_items
