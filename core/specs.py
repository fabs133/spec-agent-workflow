"""
Pure specification functions for the text extraction workflow.

RULES (non-negotiable):
    - No file IO, no network calls, no database access
    - No mutation of context (read-only)
    - Deterministic: same input -> same output
    - Return SpecResult

Each function takes a Context and returns a SpecResult.
These are registered by name so the manifest can reference them as strings.
"""

from __future__ import annotations

from typing import Callable, Dict

from core.models import Context, SpecResult

# Registry: spec_name -> spec function
_SPEC_REGISTRY: Dict[str, Callable[[Context], SpecResult]] = {}


def register_spec(name: str):
    """Decorator to register a spec function by name."""
    def decorator(fn: Callable[[Context], SpecResult]):
        _SPEC_REGISTRY[name] = fn
        return fn
    return decorator


def get_spec(name: str) -> Callable[[Context], SpecResult]:
    """Look up a spec function by name. Raises KeyError if not found."""
    if name not in _SPEC_REGISTRY:
        raise KeyError(f"Unknown spec: '{name}'. Available: {list(_SPEC_REGISTRY.keys())}")
    return _SPEC_REGISTRY[name]


def evaluate_specs(names: list[str], context: Context) -> list[SpecResult]:
    """Evaluate a list of specs against a context. Returns all results."""
    results = []
    for name in names:
        fn = get_spec(name)
        results.append(fn(context))
    return results


def all_passed(results: list[SpecResult]) -> bool:
    """Check if all spec results passed."""
    return all(r.passed for r in results)


# ---------------------------------------------------------------------------
# Intake step specs
# ---------------------------------------------------------------------------

@register_spec("intake_pre")
def intake_pre(context: Context) -> SpecResult:
    """Pre-condition: input_folder must be set and non-empty."""
    folder = context.data.get("input_folder", "")
    if not folder:
        return SpecResult(
            rule_id="intake_pre",
            passed=False,
            message="input_folder is not set in context.data",
            suggested_fix="Set context.data['input_folder'] to a valid directory path",
            tags=["pre", "intake"],
        )
    return SpecResult(
        rule_id="intake_pre",
        passed=True,
        message=f"input_folder is set: {folder}",
        tags=["pre", "intake"],
    )


@register_spec("intake_post")
def intake_post(context: Context) -> SpecResult:
    """Post-condition: loaded_files must be a non-empty list."""
    files = context.data.get("loaded_files", [])
    if not isinstance(files, list) or len(files) == 0:
        return SpecResult(
            rule_id="intake_post",
            passed=False,
            message="No files were loaded",
            suggested_fix="Ensure input_folder contains .txt or .md files",
            tags=["post", "intake"],
        )
    return SpecResult(
        rule_id="intake_post",
        passed=True,
        message=f"{len(files)} file(s) loaded",
        tags=["post", "intake"],
    )


# ---------------------------------------------------------------------------
# Extract step specs
# ---------------------------------------------------------------------------

@register_spec("extract_pre")
def extract_pre(context: Context) -> SpecResult:
    """Pre-condition: loaded_files must exist and api_key must be configured."""
    files = context.data.get("loaded_files", [])
    api_key = context.config.get("api_key", "")

    if not files:
        return SpecResult(
            rule_id="extract_pre",
            passed=False,
            message="No loaded_files in context",
            suggested_fix="Run the intake step first to load files",
            tags=["pre", "extract"],
        )
    if not api_key:
        return SpecResult(
            rule_id="extract_pre",
            passed=False,
            message="api_key is not configured",
            suggested_fix="Set the OpenAI API key in settings",
            tags=["pre", "extract", "config"],
        )
    return SpecResult(
        rule_id="extract_pre",
        passed=True,
        message=f"{len(files)} file(s) ready, API key configured",
        tags=["pre", "extract"],
    )


@register_spec("extract_post")
def extract_post(context: Context) -> SpecResult:
    """Post-condition: extracted_items must be non-empty, each with a title."""
    items = context.data.get("extracted_items", [])
    if not isinstance(items, list) or len(items) == 0:
        return SpecResult(
            rule_id="extract_post",
            passed=False,
            message="No items were extracted",
            suggested_fix="Check LLM response format or input file content",
            tags=["post", "extract"],
        )
    missing_titles = [i for i, item in enumerate(items) if not item.get("title")]
    if missing_titles:
        return SpecResult(
            rule_id="extract_post",
            passed=False,
            message=f"Items at indices {missing_titles} have no title",
            suggested_fix="Ensure LLM prompt requires a title for each item",
            tags=["post", "extract", "schema"],
        )
    return SpecResult(
        rule_id="extract_post",
        passed=True,
        message=f"{len(items)} item(s) extracted, all with titles",
        tags=["post", "extract"],
    )


# ---------------------------------------------------------------------------
# Write step specs
# ---------------------------------------------------------------------------

@register_spec("write_pre")
def write_pre(context: Context) -> SpecResult:
    """Pre-condition: extracted_items and output_folder must exist."""
    items = context.data.get("extracted_items", [])
    folder = context.data.get("output_folder", "")

    if not items:
        return SpecResult(
            rule_id="write_pre",
            passed=False,
            message="No extracted_items to write",
            suggested_fix="Run the extract step first",
            tags=["pre", "write"],
        )
    if not folder:
        return SpecResult(
            rule_id="write_pre",
            passed=False,
            message="output_folder is not set",
            suggested_fix="Set context.data['output_folder'] to a valid directory path",
            tags=["pre", "write"],
        )
    return SpecResult(
        rule_id="write_pre",
        passed=True,
        message=f"{len(items)} item(s) ready, output_folder set: {folder}",
        tags=["pre", "write"],
    )


@register_spec("write_post")
def write_post(context: Context) -> SpecResult:
    """Post-condition: written_files must be non-empty."""
    written = context.data.get("written_files", [])
    if not isinstance(written, list) or len(written) == 0:
        return SpecResult(
            rule_id="write_post",
            passed=False,
            message="No files were written",
            suggested_fix="Check output_folder permissions and disk space",
            tags=["post", "write"],
        )
    return SpecResult(
        rule_id="write_post",
        passed=True,
        message=f"{len(written)} file(s) written",
        tags=["post", "write"],
    )


# ---------------------------------------------------------------------------
# Global / invariant specs
# ---------------------------------------------------------------------------

@register_spec("global_invariant")
def global_invariant(context: Context) -> SpecResult:
    """Invariant: run_id must always be set."""
    if not context.run_id:
        return SpecResult(
            rule_id="global_invariant",
            passed=False,
            message="run_id is missing from context",
            suggested_fix="This is an internal error - context was not initialized properly",
            tags=["invariant"],
        )
    return SpecResult(
        rule_id="global_invariant",
        passed=True,
        message=f"run_id={context.run_id[:8]}...",
        tags=["invariant"],
    )


# ---------------------------------------------------------------------------
# Progress spec
# ---------------------------------------------------------------------------

@register_spec("pipeline_progress")
def pipeline_progress(context: Context) -> SpecResult:
    """Progress: compute 0.0-1.0 based on what data exists in context."""
    score = 0.0
    if context.data.get("loaded_files"):
        score += 0.33
    if context.data.get("extracted_items"):
        score += 0.33
    if context.data.get("written_files"):
        score += 0.34

    return SpecResult(
        rule_id="pipeline_progress",
        passed=True,
        message=f"Progress: {score:.0%}",
        tags=["progress"],
    )
