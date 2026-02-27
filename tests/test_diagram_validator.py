"""Tests for diagrams.validator."""

from diagrams.models import Diagram, DiagramEdge, DiagramNode
from diagrams.validator import validate_diagram


class TestValidDiagram:
    def test_valid_returns_empty(self):
        diagram = Diagram(
            title="Valid",
            diagram_type="component",
            nodes=[
                DiagramNode(id="a", label="A", node_type="module"),
                DiagramNode(id="b", label="B", node_type="module"),
            ],
            edges=[
                DiagramEdge(id="e1", source_id="a", target_id="b"),
            ],
        )
        assert validate_diagram(diagram) == []


class TestDuplicateNodeIds:
    def test_detected(self):
        diagram = Diagram(
            title="Dup",
            diagram_type="component",
            nodes=[
                DiagramNode(id="a", label="A", node_type="module"),
                DiagramNode(id="a", label="A2", node_type="module"),
            ],
            edges=[
                DiagramEdge(id="e1", source_id="a", target_id="a"),
            ],
        )
        errors = validate_diagram(diagram)
        assert any("duplicate" in e.lower() for e in errors)


class TestDanglingEdge:
    def test_detected(self):
        diagram = Diagram(
            title="Dangling",
            diagram_type="component",
            nodes=[
                DiagramNode(id="a", label="A", node_type="module"),
            ],
            edges=[
                DiagramEdge(id="e1", source_id="a", target_id="missing"),
            ],
        )
        errors = validate_diagram(diagram)
        assert any("target" in e.lower() for e in errors)

    def test_missing_source(self):
        diagram = Diagram(
            title="Dangling source",
            diagram_type="component",
            nodes=[
                DiagramNode(id="b", label="B", node_type="module"),
            ],
            edges=[
                DiagramEdge(id="e1", source_id="ghost", target_id="b"),
            ],
        )
        errors = validate_diagram(diagram)
        assert any("source" in e.lower() for e in errors)


class TestOrphanNode:
    def test_detected(self):
        diagram = Diagram(
            title="Orphan",
            diagram_type="component",
            nodes=[
                DiagramNode(id="a", label="A", node_type="module"),
                DiagramNode(id="b", label="B", node_type="module"),
                DiagramNode(id="lonely", label="Lonely", node_type="module"),
            ],
            edges=[
                DiagramEdge(id="e1", source_id="a", target_id="b"),
            ],
        )
        errors = validate_diagram(diagram)
        assert any("orphan" in e.lower() or "unreferenced" in e.lower() for e in errors)

    def test_boundary_not_flagged(self):
        diagram = Diagram(
            title="Boundary OK",
            diagram_type="component",
            nodes=[
                DiagramNode(id="boundary", label="Pkg", node_type="boundary"),
                DiagramNode(id="a", label="A", node_type="module", parent_id="boundary"),
                DiagramNode(id="b", label="B", node_type="module", parent_id="boundary"),
            ],
            edges=[
                DiagramEdge(id="e1", source_id="a", target_id="b"),
            ],
        )
        errors = validate_diagram(diagram)
        assert errors == []


class TestStateDiagramChecks:
    def test_missing_initial(self):
        diagram = Diagram(
            title="No initial",
            diagram_type="state",
            nodes=[
                DiagramNode(id="s1", label="S1", node_type="state"),
                DiagramNode(id="f", label="", node_type="final"),
            ],
            edges=[
                DiagramEdge(id="e1", source_id="s1", target_id="f"),
            ],
        )
        errors = validate_diagram(diagram)
        assert any("initial" in e.lower() for e in errors)

    def test_missing_final(self):
        diagram = Diagram(
            title="No final",
            diagram_type="state",
            nodes=[
                DiagramNode(id="i", label="", node_type="initial"),
                DiagramNode(id="s1", label="S1", node_type="state"),
            ],
            edges=[
                DiagramEdge(id="e1", source_id="i", target_id="s1"),
            ],
        )
        errors = validate_diagram(diagram)
        assert any("final" in e.lower() for e in errors)


class TestEmptyDiagram:
    def test_no_nodes(self):
        diagram = Diagram(title="Empty", diagram_type="component")
        errors = validate_diagram(diagram)
        assert any("no nodes" in e.lower() for e in errors)
