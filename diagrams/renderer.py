"""Render Diagram objects to Draw.io XML format.

Uses ``xml.etree.ElementTree`` for XML construction, which handles
escaping of special characters automatically.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict

from diagrams.models import Diagram, DiagramEdge, DiagramNode
from diagrams.styles import (
    STYLE_ACTOR,
    STYLE_ASSOCIATION,
    STYLE_DEPENDENCY_EDGE,
    STYLE_IMPORT_EDGE,
    STYLE_MODULE_BOX,
    STYLE_PACKAGE_BOUNDARY,
    STYLE_STATE,
    STYLE_STATE_FINAL,
    STYLE_STATE_INITIAL,
    STYLE_SYSTEM_BOUNDARY,
    STYLE_TRANSITION,
    STYLE_TRANSITION_FAIL,
    STYLE_USECASE,
)

# Mapping: node_type → style string
_NODE_STYLES: Dict[str, str] = {
    "module": STYLE_MODULE_BOX,
    "boundary": STYLE_PACKAGE_BOUNDARY,  # overridden for usecase
    "actor": STYLE_ACTOR,
    "usecase": STYLE_USECASE,
    "state": STYLE_STATE,
    "initial": STYLE_STATE_INITIAL,
    "final": STYLE_STATE_FINAL,
}

# Mapping: edge_type → style string
_EDGE_STYLES: Dict[str, str] = {
    "solid": STYLE_DEPENDENCY_EDGE,
    "dashed": STYLE_IMPORT_EDGE,
    "association": STYLE_ASSOCIATION,
    "transition": STYLE_TRANSITION,
    "transition_fail": STYLE_TRANSITION_FAIL,
}


def _node_style(node: DiagramNode, diagram_type: str) -> str:
    """Resolve the Draw.io style string for a node."""
    if node.node_type == "boundary":
        if diagram_type == "usecase":
            return STYLE_SYSTEM_BOUNDARY
        return STYLE_PACKAGE_BOUNDARY
    return _NODE_STYLES.get(node.node_type, STYLE_MODULE_BOX)


def _edge_style(edge: DiagramEdge) -> str:
    """Resolve the Draw.io style string for an edge."""
    return _EDGE_STYLES.get(edge.edge_type, STYLE_DEPENDENCY_EDGE)


def render_drawio(diagram: Diagram) -> str:
    """Render a :class:`Diagram` as a Draw.io ``.drawio`` XML string."""
    mxfile = ET.Element("mxfile", {
        "host": "app.diagrams.net",
        "type": "device",
    })
    diag_el = ET.SubElement(mxfile, "diagram", {
        "id": "diagram_1",
        "name": diagram.title,
    })
    model = ET.SubElement(diag_el, "mxGraphModel", {
        "dx": "1420",
        "dy": "800",
        "grid": "1",
        "gridSize": "10",
        "guides": "1",
        "tooltips": "1",
        "connect": "1",
        "arrows": "1",
        "fold": "1",
        "page": "1",
        "pageScale": "1",
        "pageWidth": str(diagram.page_width),
        "pageHeight": str(diagram.page_height),
    })
    root = ET.SubElement(model, "root")

    # Root cells (required by Draw.io)
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    # Render nodes
    for node in diagram.nodes:
        style = _node_style(node, diagram.diagram_type)
        parent = node.parent_id if node.parent_id else "1"
        cell = ET.SubElement(root, "mxCell", {
            "id": node.id,
            "value": node.label,
            "style": style,
            "vertex": "1",
            "parent": parent,
        })
        ET.SubElement(cell, "mxGeometry", {
            "x": str(node.x),
            "y": str(node.y),
            "width": str(node.width),
            "height": str(node.height),
            "as": "geometry",
        })

    # Render edges
    for edge in diagram.edges:
        style = _edge_style(edge)
        cell = ET.SubElement(root, "mxCell", {
            "id": edge.id,
            "value": edge.label,
            "style": style,
            "edge": "1",
            "parent": "1",
            "source": edge.source_id,
            "target": edge.target_id,
        })
        ET.SubElement(cell, "mxGeometry", {
            "relative": "1",
            "as": "geometry",
        })

    # Serialize to string
    ET.indent(mxfile, space="  ")
    return ET.tostring(mxfile, encoding="unicode", xml_declaration=True)


def save_drawio(xml_content: str, output_path: Path) -> Path:
    """Write *xml_content* to a ``.drawio`` file at *output_path*.

    Creates parent directories if they do not exist.
    Returns the resolved output path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(xml_content, encoding="utf-8")
    return output_path.resolve()
