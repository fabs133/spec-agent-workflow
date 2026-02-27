"""Tests for diagrams.renderer."""

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from diagrams.models import Diagram, DiagramEdge, DiagramNode
from diagrams.renderer import render_drawio, save_drawio


def _minimal_diagram():
    return Diagram(
        title="Test Diagram",
        diagram_type="component",
        nodes=[
            DiagramNode(id="n1", label="Node One", node_type="module", x=10, y=20),
            DiagramNode(id="n2", label="Node Two", node_type="module", x=200, y=20),
        ],
        edges=[
            DiagramEdge(id="e1", source_id="n1", target_id="n2", label="imports"),
        ],
    )


class TestRenderMinimal:
    def test_produces_mxfile(self):
        xml = render_drawio(_minimal_diagram())
        assert "<mxfile" in xml

    def test_contains_node_ids(self):
        xml = render_drawio(_minimal_diagram())
        assert 'id="n1"' in xml
        assert 'id="n2"' in xml

    def test_contains_edge(self):
        xml = render_drawio(_minimal_diagram())
        assert 'edge="1"' in xml

    def test_wellformed_xml(self):
        xml = render_drawio(_minimal_diagram())
        # Should not raise
        tree = ET.fromstring(xml)
        assert tree.tag == "mxfile"


class TestEscaping:
    def test_special_chars_in_label(self):
        diagram = Diagram(
            title="Escape Test",
            diagram_type="component",
            nodes=[
                DiagramNode(id="n1", label="Workflow & Modell", node_type="module"),
                DiagramNode(id="n2", label='Tag "test"', node_type="module"),
            ],
            edges=[
                DiagramEdge(id="e1", source_id="n1", target_id="n2"),
            ],
        )
        xml = render_drawio(diagram)
        # ET escapes & as &amp; and " in attributes
        assert "&amp;" in xml or "Workflow &amp; Modell" in xml
        # Must still be valid XML
        ET.fromstring(xml)

    def test_umlauts(self):
        diagram = Diagram(
            title="Umlaut Test",
            diagram_type="usecase",
            nodes=[
                DiagramNode(id="n1", label="Pr\u00e4sentation", node_type="usecase"),
                DiagramNode(id="n2", label="f\u00fcr", node_type="usecase"),
            ],
            edges=[
                DiagramEdge(id="e1", source_id="n1", target_id="n2"),
            ],
        )
        xml = render_drawio(diagram)
        ET.fromstring(xml)  # Must be valid


class TestParentRelationship:
    def test_parent_in_mxcell(self):
        diagram = Diagram(
            title="Parent Test",
            diagram_type="component",
            nodes=[
                DiagramNode(id="boundary", label="Pkg", node_type="boundary"),
                DiagramNode(id="child", label="Mod", node_type="module", parent_id="boundary"),
            ],
            edges=[],
        )
        xml = render_drawio(diagram)
        # The child mxCell should have parent="boundary"
        tree = ET.fromstring(xml)
        root_el = tree.find(".//root")
        child_cell = None
        for cell in root_el.findall("mxCell"):
            if cell.get("id") == "child":
                child_cell = cell
                break
        assert child_cell is not None
        assert child_cell.get("parent") == "boundary"


class TestSaveDrawio:
    def test_creates_file(self):
        xml = render_drawio(_minimal_diagram())
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "test.drawio"
            result = save_drawio(xml, out)
            assert out.exists()
            content = out.read_text(encoding="utf-8")
            assert content.startswith("<?xml")
            assert "<mxfile" in content

    def test_creates_subdirectories(self):
        xml = render_drawio(_minimal_diagram())
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "sub" / "dir" / "test.drawio"
            save_drawio(xml, out)
            assert out.exists()
