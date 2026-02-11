"""Tests for pure spec functions.

Specs are the most testable part of the system:
no IO, no mocking, fully deterministic.
"""

from core.models import Context, SpecResult
from core.specs import (
    evaluate_specs,
    all_passed,
    get_spec,
    intake_pre,
    intake_post,
    extract_pre,
    extract_post,
    write_pre,
    write_post,
    global_invariant,
    pipeline_progress,
)


# ---------------------------------------------------------------------------
# intake_pre
# ---------------------------------------------------------------------------

class TestIntakePre:
    def test_passes_when_folder_set(self, sample_context):
        result = intake_pre(sample_context)
        assert result.passed is True
        assert "input_folder" in result.message

    def test_fails_when_folder_missing(self, empty_context):
        result = intake_pre(empty_context)
        assert result.passed is False
        assert result.suggested_fix

    def test_fails_when_folder_empty_string(self):
        ctx = Context(data={"input_folder": ""})
        result = intake_pre(ctx)
        assert result.passed is False


# ---------------------------------------------------------------------------
# intake_post
# ---------------------------------------------------------------------------

class TestIntakePost:
    def test_passes_when_files_loaded(self, context_after_intake):
        result = intake_post(context_after_intake)
        assert result.passed is True
        assert "2" in result.message

    def test_fails_when_no_files(self, sample_context):
        result = intake_post(sample_context)
        assert result.passed is False

    def test_fails_when_files_empty_list(self):
        ctx = Context(data={"loaded_files": []})
        result = intake_post(ctx)
        assert result.passed is False


# ---------------------------------------------------------------------------
# extract_pre
# ---------------------------------------------------------------------------

class TestExtractPre:
    def test_passes_when_files_and_key(self, context_after_intake):
        result = extract_pre(context_after_intake)
        assert result.passed is True

    def test_fails_when_no_files(self, sample_context):
        result = extract_pre(sample_context)
        assert result.passed is False
        assert "loaded_files" in result.message

    def test_fails_when_no_api_key(self, context_after_intake):
        context_after_intake.config["api_key"] = ""
        result = extract_pre(context_after_intake)
        assert result.passed is False
        assert "api_key" in result.message


# ---------------------------------------------------------------------------
# extract_post
# ---------------------------------------------------------------------------

class TestExtractPost:
    def test_passes_when_items_extracted(self, context_after_extract):
        result = extract_post(context_after_extract)
        assert result.passed is True

    def test_fails_when_no_items(self, context_after_intake):
        result = extract_post(context_after_intake)
        assert result.passed is False

    def test_fails_when_item_missing_title(self):
        ctx = Context(data={
            "extracted_items": [
                {"title": "Good item", "item_type": "task"},
                {"item_type": "bug"},  # missing title
            ]
        })
        result = extract_post(ctx)
        assert result.passed is False
        assert "1" in result.message  # index 1 has no title


# ---------------------------------------------------------------------------
# write_pre
# ---------------------------------------------------------------------------

class TestWritePre:
    def test_passes_when_items_and_folder(self, context_after_extract):
        result = write_pre(context_after_extract)
        assert result.passed is True

    def test_fails_when_no_items(self, sample_context):
        result = write_pre(sample_context)
        assert result.passed is False

    def test_fails_when_no_output_folder(self):
        ctx = Context(data={"extracted_items": [{"title": "x"}]})
        result = write_pre(ctx)
        assert result.passed is False
        assert "output_folder" in result.message


# ---------------------------------------------------------------------------
# write_post
# ---------------------------------------------------------------------------

class TestWritePost:
    def test_passes_when_files_written(self, context_after_write):
        result = write_post(context_after_write)
        assert result.passed is True

    def test_fails_when_no_files_written(self, context_after_extract):
        result = write_post(context_after_extract)
        assert result.passed is False


# ---------------------------------------------------------------------------
# global_invariant
# ---------------------------------------------------------------------------

class TestGlobalInvariant:
    def test_passes_with_run_id(self, sample_context):
        result = global_invariant(sample_context)
        assert result.passed is True

    def test_fails_without_run_id(self):
        ctx = Context(run_id="")
        result = global_invariant(ctx)
        assert result.passed is False


# ---------------------------------------------------------------------------
# pipeline_progress
# ---------------------------------------------------------------------------

class TestPipelineProgress:
    def test_zero_at_start(self, empty_context):
        result = pipeline_progress(empty_context)
        assert result.passed is True
        assert "0%" in result.message

    def test_33_after_intake(self, context_after_intake):
        result = pipeline_progress(context_after_intake)
        assert "33%" in result.message

    def test_66_after_extract(self, context_after_extract):
        result = pipeline_progress(context_after_extract)
        assert "66%" in result.message

    def test_100_after_write(self, context_after_write):
        result = pipeline_progress(context_after_write)
        assert "100%" in result.message


# ---------------------------------------------------------------------------
# Registry and helpers
# ---------------------------------------------------------------------------

class TestSpecRegistry:
    def test_get_spec_returns_function(self):
        fn = get_spec("intake_pre")
        assert callable(fn)

    def test_get_spec_unknown_raises(self):
        try:
            get_spec("nonexistent_spec")
            assert False, "Should have raised KeyError"
        except KeyError:
            pass

    def test_evaluate_specs_returns_all_results(self, sample_context):
        results = evaluate_specs(["intake_pre", "global_invariant"], sample_context)
        assert len(results) == 2
        assert all(isinstance(r, SpecResult) for r in results)

    def test_all_passed_true(self, sample_context):
        results = evaluate_specs(["intake_pre", "global_invariant"], sample_context)
        assert all_passed(results) is True

    def test_all_passed_false_when_one_fails(self, empty_context):
        results = evaluate_specs(["intake_pre", "global_invariant"], empty_context)
        assert all_passed(results) is False


# ---------------------------------------------------------------------------
# SpecResult determinism: same input -> same output
# ---------------------------------------------------------------------------

class TestSpecDeterminism:
    def test_same_input_same_output(self, sample_context):
        r1 = intake_pre(sample_context)
        r2 = intake_pre(sample_context)
        assert r1.passed == r2.passed
        assert r1.message == r2.message
        assert r1.rule_id == r2.rule_id
