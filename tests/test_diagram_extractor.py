"""Tests for diagrams.extractor."""

from pathlib import Path

from diagrams.extractor import (
    extract_module_graph,
    extract_usecases,
    extract_workflow_states,
)

PROJECT_ROOT = Path(__file__).parent.parent
MANIFEST_PATH = PROJECT_ROOT / "manifests" / "text_extraction.json"


class TestExtractModuleGraph:
    def test_finds_core_modules(self):
        data = extract_module_graph(PROJECT_ROOT)
        names = {m["name"] for m in data["modules"]}
        assert "core.specs" in names
        assert "core.models" in names
        assert "core.orchestrator" in names

    def test_ignores_stdlib(self):
        data = extract_module_graph(PROJECT_ROOT)
        import_targets = {imp["to"] for imp in data["imports"]}
        for stdlib in ("json", "pathlib", "dataclasses", "os", "sys", "ast"):
            assert stdlib not in import_targets

    def test_finds_classes(self):
        data = extract_module_graph(PROJECT_ROOT)
        models_mod = None
        for m in data["modules"]:
            if m["name"] == "core.models":
                models_mod = m
                break
        assert models_mod is not None
        assert "RunStatus" in models_mod["classes"]
        assert "StepStatus" in models_mod["classes"]
        assert "SpecResult" in models_mod["classes"]
        assert "Context" in models_mod["classes"]

    def test_has_imports(self):
        data = extract_module_graph(PROJECT_ROOT)
        assert len(data["imports"]) >= 5

    def test_modules_have_expected_fields(self):
        data = extract_module_graph(PROJECT_ROOT)
        for mod in data["modules"]:
            assert "name" in mod
            assert "docstring" in mod
            assert "classes" in mod
            assert "functions" in mod
            assert "file" in mod


class TestExtractWorkflowStates:
    def test_three_states(self):
        data = extract_workflow_states(MANIFEST_PATH)
        names = {s["name"] for s in data["states"]}
        assert names == {"intake", "extract", "write"}

    def test_two_transitions(self):
        data = extract_workflow_states(MANIFEST_PATH)
        assert len(data["transitions"]) == 2
        t_pairs = [(t["from"], t["to"]) for t in data["transitions"]]
        assert ("intake", "extract") in t_pairs
        assert ("extract", "write") in t_pairs

    def test_entry_step(self):
        data = extract_workflow_states(MANIFEST_PATH)
        assert data["entry_step"] == "intake"

    def test_budgets(self):
        data = extract_workflow_states(MANIFEST_PATH)
        assert "max_retries_per_step" in data["budgets"]


class TestExtractUsecases:
    def test_actors(self):
        data = extract_usecases(PROJECT_ROOT)
        actor_ids = {a["id"] for a in data["actors"]}
        assert actor_ids == {"projektplaner", "teamleiter", "admin"}

    def test_usecases_count(self):
        data = extract_usecases(PROJECT_ROOT)
        assert len(data["usecases"]) == 7

    def test_associations_count(self):
        data = extract_usecases(PROJECT_ROOT)
        assert len(data["associations"]) == 12

    def test_system_name(self):
        data = extract_usecases(PROJECT_ROOT)
        assert "system_name" in data
        assert len(data["system_name"]) > 0
