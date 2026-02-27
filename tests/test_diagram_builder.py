"""Tests for diagrams.builder."""

from pathlib import Path

from diagrams.builder import (
    build_component_diagram,
    build_state_diagram,
    build_usecase_diagram,
)
from diagrams.extractor import extract_usecases, extract_workflow_states

PROJECT_ROOT = Path(__file__).parent.parent
MANIFEST_PATH = PROJECT_ROOT / "manifests" / "text_extraction.json"


class TestBuildComponentDiagram:
    def test_has_packages(self):
        module_data = {
            "modules": [
                {"name": "pkgA.mod1", "docstring": "", "classes": [], "functions": [], "file": "pkgA/mod1.py"},
                {"name": "pkgA.mod2", "docstring": "", "classes": [], "functions": [], "file": "pkgA/mod2.py"},
                {"name": "pkgB.mod3", "docstring": "", "classes": [], "functions": [], "file": "pkgB/mod3.py"},
                {"name": "pkgB.mod4", "docstring": "", "classes": [], "functions": [], "file": "pkgB/mod4.py"},
            ],
            "imports": [
                {"from": "pkgA.mod1", "to": "pkgA.mod2", "names": ["X"]},
                {"from": "pkgA.mod1", "to": "pkgB.mod3", "names": ["Y"]},
            ],
        }
        diagram = build_component_diagram(module_data)
        boundary_nodes = [n for n in diagram.nodes if n.node_type == "boundary"]
        module_nodes = [n for n in diagram.nodes if n.node_type == "module"]
        assert len(boundary_nodes) == 2
        assert len(module_nodes) == 4
        assert len(diagram.edges) == 2

    def test_cross_package_edge_is_dashed(self):
        module_data = {
            "modules": [
                {"name": "a.x", "docstring": "", "classes": [], "functions": [], "file": "a/x.py"},
                {"name": "b.y", "docstring": "", "classes": [], "functions": [], "file": "b/y.py"},
            ],
            "imports": [
                {"from": "a.x", "to": "b.y", "names": ["Z"]},
            ],
        }
        diagram = build_component_diagram(module_data)
        assert diagram.edges[0].edge_type == "dashed"


class TestBuildStateDiagram:
    def test_has_initial_and_final(self):
        data = extract_workflow_states(MANIFEST_PATH)
        diagram = build_state_diagram(data)
        initial = [n for n in diagram.nodes if n.node_type == "initial"]
        final = [n for n in diagram.nodes if n.node_type == "final"]
        states = [n for n in diagram.nodes if n.node_type == "state"]
        assert len(initial) == 1
        assert len(final) == 1
        assert len(states) == 3

    def test_edges(self):
        data = extract_workflow_states(MANIFEST_PATH)
        diagram = build_state_diagram(data)
        edge_pairs = [(e.source_id, e.target_id) for e in diagram.edges if e.edge_type == "transition"]
        assert ("__initial__", "intake") in edge_pairs
        assert ("intake", "extract") in edge_pairs
        assert ("extract", "write") in edge_pairs
        assert ("write", "__final__") in edge_pairs

    def test_title(self):
        data = extract_workflow_states(MANIFEST_PATH)
        diagram = build_state_diagram(data)
        assert "Zustandsdiagramm" in diagram.title


class TestBuildUsecaseDiagram:
    def test_structure(self):
        data = extract_usecases(PROJECT_ROOT)
        diagram = build_usecase_diagram(data)
        actors = [n for n in diagram.nodes if n.node_type == "actor"]
        usecases = [n for n in diagram.nodes if n.node_type == "usecase"]
        boundaries = [n for n in diagram.nodes if n.node_type == "boundary"]
        assert len(actors) == 3
        assert len(usecases) == 7
        assert len(boundaries) == 1
        assert len(diagram.edges) == 12
