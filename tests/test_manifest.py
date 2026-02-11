"""Tests for manifest loading, step definitions, and router."""

from pathlib import Path

import pytest

from core.manifest import Manifest
from core.router import Edge, Router
from core.steps import StepDefinition, RetryPolicy
from core.errors import ManifestError


FIXTURES = Path(__file__).parent / "fixtures"
MANIFESTS = Path(__file__).parent.parent / "manifests"


class TestManifestLoading:
    def test_load_sample_manifest(self):
        m = Manifest.from_yaml(FIXTURES / "sample_manifest.yaml")
        assert m.name == "test_workflow"
        assert m.entry_step == "step_a"
        assert len(m.steps) == 2
        assert len(m.edges) == 2

    def test_load_production_manifest(self):
        m = Manifest.from_yaml(MANIFESTS / "text_extraction.yaml")
        assert m.name == "text_extraction"
        assert m.entry_step == "intake"
        assert len(m.steps) == 3
        assert "intake" in m.steps
        assert "extract" in m.steps
        assert "write" in m.steps

    def test_steps_have_correct_agents(self):
        m = Manifest.from_yaml(MANIFESTS / "text_extraction.yaml")
        assert m.steps["intake"].agent_name == "intake_agent"
        assert m.steps["extract"].agent_name == "extract_agent"
        assert m.steps["write"].agent_name == "write_agent"

    def test_steps_have_specs(self):
        m = Manifest.from_yaml(MANIFESTS / "text_extraction.yaml")
        assert "intake_pre" in m.steps["intake"].pre_specs
        assert "intake_post" in m.steps["intake"].post_specs
        assert "global_invariant" in m.steps["intake"].invariant_specs

    def test_steps_have_retry_policy(self):
        m = Manifest.from_yaml(MANIFESTS / "text_extraction.yaml")
        assert m.steps["extract"].retry.max_attempts == 3
        assert m.steps["extract"].retry.delay_seconds == 2.0

    def test_edges_parsed(self):
        m = Manifest.from_yaml(MANIFESTS / "text_extraction.yaml")
        edges = m.edges
        assert any(e.from_step == "intake" and e.to_step == "extract" for e in edges)
        assert any(e.from_step == "extract" and e.to_step == "write" for e in edges)

    def test_defaults_loaded(self):
        m = Manifest.from_yaml(MANIFESTS / "text_extraction.yaml")
        assert m.defaults["model"] == "gpt-4o"
        assert m.defaults["temperature"] == 0.3

    def test_budgets_loaded(self):
        m = Manifest.from_yaml(MANIFESTS / "text_extraction.yaml")
        assert m.budgets["max_retries_per_step"] == 3
        assert m.budgets["max_total_steps"] == 20


class TestManifestValidation:
    def test_missing_name_raises(self):
        with pytest.raises(ManifestError, match="name"):
            Manifest.from_dict({"entry_step": "x", "steps": {"x": {"agent": "a"}}})

    def test_missing_entry_step_raises(self):
        with pytest.raises(ManifestError, match="entry_step"):
            Manifest.from_dict({"name": "test", "steps": {"x": {"agent": "a"}}})

    def test_empty_steps_raises(self):
        with pytest.raises(ManifestError, match="at least one step"):
            Manifest.from_dict({"name": "test", "entry_step": "x", "steps": {}})

    def test_entry_step_not_in_steps_raises(self):
        with pytest.raises(ManifestError, match="not found"):
            Manifest.from_dict({
                "name": "test",
                "entry_step": "missing",
                "steps": {"existing": {"agent": "a"}},
            })

    def test_step_without_agent_raises(self):
        with pytest.raises(ManifestError, match="agent"):
            Manifest.from_dict({
                "name": "test",
                "entry_step": "x",
                "steps": {"x": {"specs": {}}},
            })

    def test_nonexistent_file_raises(self):
        with pytest.raises(ManifestError, match="not found"):
            Manifest.from_yaml("/nonexistent/path.yaml")


class TestManifestFromDict:
    def test_minimal_manifest(self):
        m = Manifest.from_dict({
            "name": "minimal",
            "entry_step": "only_step",
            "steps": {
                "only_step": {"agent": "my_agent"},
            },
        })
        assert m.name == "minimal"
        assert len(m.steps) == 1
        assert m.steps["only_step"].agent_name == "my_agent"
        assert m.steps["only_step"].pre_specs == []
        assert m.edges == []


class TestRouter:
    def setup_method(self):
        self.edges = [
            Edge(from_step="intake", to_step="extract", condition="on_pass"),
            Edge(from_step="intake", to_step="__end__", condition="on_fail"),
            Edge(from_step="extract", to_step="write", condition="on_pass"),
            Edge(from_step="extract", to_step="__end__", condition="on_fail"),
            Edge(from_step="write", to_step="__end__", condition="always"),
        ]
        self.router = Router(self.edges)

    def test_next_on_pass(self):
        assert self.router.next_step("intake", step_passed=True) == "extract"

    def test_next_on_fail(self):
        assert self.router.next_step("intake", step_passed=False) == "__end__"

    def test_always_condition(self):
        assert self.router.next_step("write", step_passed=True) == "__end__"
        assert self.router.next_step("write", step_passed=False) == "__end__"

    def test_no_matching_edge_returns_none(self):
        assert self.router.next_step("nonexistent", step_passed=True) is None

    def test_get_all_edges_from(self):
        edges = self.router.get_all_edges_from("intake")
        assert len(edges) == 2

    def test_get_step_names(self):
        names = self.router.get_step_names()
        assert "intake" in names
        assert "extract" in names
        assert "write" in names
        assert "__end__" not in names  # excluded


class TestStepDefinition:
    def test_default_retry_policy(self):
        step = StepDefinition(name="test", agent_name="agent")
        assert step.retry.max_attempts == 2
        assert step.retry.delay_seconds == 1.0

    def test_empty_specs_by_default(self):
        step = StepDefinition(name="test", agent_name="agent")
        assert step.pre_specs == []
        assert step.post_specs == []
        assert step.invariant_specs == []
