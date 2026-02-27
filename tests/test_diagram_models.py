"""Tests for diagrams.models dataclasses."""

from diagrams.models import Diagram, DiagramEdge, DiagramNode, DiagramType


class TestDiagramNode:
    def test_creation_with_defaults(self):
        node = DiagramNode(id="n1", label="Test", node_type="module")
        assert node.id == "n1"
        assert node.label == "Test"
        assert node.node_type == "module"
        assert node.x == 0
        assert node.y == 0
        assert node.width == 160
        assert node.height == 60
        assert node.parent_id is None
        assert node.metadata == {}

    def test_creation_with_custom_values(self):
        node = DiagramNode(
            id="n2", label="Custom", node_type="actor",
            x=100, y=200, width=80, height=40,
            parent_id="boundary1",
            metadata={"role": "admin"},
        )
        assert node.x == 100
        assert node.parent_id == "boundary1"
        assert node.metadata["role"] == "admin"


class TestDiagramEdge:
    def test_creation_with_defaults(self):
        edge = DiagramEdge(id="e1", source_id="n1", target_id="n2")
        assert edge.id == "e1"
        assert edge.source_id == "n1"
        assert edge.target_id == "n2"
        assert edge.label == ""
        assert edge.edge_type == "solid"
        assert edge.metadata == {}

    def test_creation_with_label(self):
        edge = DiagramEdge(
            id="e2", source_id="a", target_id="b",
            label="on_pass", edge_type="dashed",
        )
        assert edge.label == "on_pass"
        assert edge.edge_type == "dashed"


class TestDiagram:
    def _make_diagram(self):
        nodes = [
            DiagramNode(id="a", label="A", node_type="module"),
            DiagramNode(id="b", label="B", node_type="module"),
            DiagramNode(id="c", label="C", node_type="boundary"),
        ]
        edges = [
            DiagramEdge(id="e1", source_id="a", target_id="b"),
            DiagramEdge(id="e2", source_id="b", target_id="c"),
        ]
        return Diagram(title="Test", diagram_type="component", nodes=nodes, edges=edges)

    def test_get_node_found(self):
        d = self._make_diagram()
        node = d.get_node("a")
        assert node is not None
        assert node.label == "A"

    def test_get_node_not_found(self):
        d = self._make_diagram()
        assert d.get_node("unknown") is None

    def test_get_edges_from(self):
        d = self._make_diagram()
        edges = d.get_edges_from("a")
        assert len(edges) == 1
        assert edges[0].target_id == "b"

    def test_get_edges_to(self):
        d = self._make_diagram()
        edges = d.get_edges_to("b")
        assert len(edges) == 1
        assert edges[0].source_id == "a"

    def test_node_ids(self):
        d = self._make_diagram()
        assert d.node_ids() == {"a", "b", "c"}

    def test_empty_diagram(self):
        d = Diagram(title="Empty", diagram_type="component")
        assert d.nodes == []
        assert d.edges == []
        assert d.node_ids() == set()
        assert d.get_node("x") is None
        assert d.get_edges_from("x") == []
        assert d.get_edges_to("x") == []


class TestDiagramType:
    def test_values(self):
        assert DiagramType.COMPONENT == "component"
        assert DiagramType.STATE == "state"
        assert DiagramType.USECASE == "usecase"
