"""Dataclasses representing the internal graph model for diagram generation.

DiagramNode, DiagramEdge, and Diagram form the core data structures.
These are populated by extractors/builders and consumed by the renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class DiagramType(str, Enum):
    """Supported diagram types."""
    COMPONENT = "component"
    STATE = "state"
    USECASE = "usecase"


@dataclass
class DiagramNode:
    """A single node in the diagram graph.

    Attributes:
        id: Unique identifier (e.g. "core.specs").
        label: Display text shown in the diagram.
        node_type: Semantic type ("module", "class", "actor", "usecase",
                   "state", "boundary", "initial", "final").
        x: Horizontal position (set by layout).
        y: Vertical position (set by layout).
        width: Node width in pixels.
        height: Node height in pixels.
        parent_id: If set, this node is rendered inside the parent boundary.
        metadata: Arbitrary extra data (docstring, functions, imports, …).
    """
    id: str
    label: str
    node_type: str
    x: int = 0
    y: int = 0
    width: int = 160
    height: int = 60
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiagramEdge:
    """A directed edge between two DiagramNodes.

    Attributes:
        id: Unique edge identifier.
        source_id: Reference to the source DiagramNode.id.
        target_id: Reference to the target DiagramNode.id.
        label: Optional label displayed on the edge (e.g. "on_pass").
        edge_type: Visual style key ("solid", "dashed", "dotted",
                   "association", "transition", "transition_fail").
        metadata: Arbitrary extra data.
    """
    id: str
    source_id: str
    target_id: str
    label: str = ""
    edge_type: str = "solid"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Diagram:
    """Complete diagram containing nodes and edges.

    Attributes:
        title: Human-readable diagram title.
        diagram_type: One of DiagramType values.
        nodes: All nodes in the diagram.
        edges: All edges in the diagram.
        page_width: Draw.io page width.
        page_height: Draw.io page height.
    """
    title: str
    diagram_type: str
    nodes: List[DiagramNode] = field(default_factory=list)
    edges: List[DiagramEdge] = field(default_factory=list)
    page_width: int = 1169
    page_height: int = 827

    def get_node(self, node_id: str) -> Optional[DiagramNode]:
        """Return the node with the given id, or None."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_edges_from(self, node_id: str) -> List[DiagramEdge]:
        """Return all edges originating from *node_id*."""
        return [e for e in self.edges if e.source_id == node_id]

    def get_edges_to(self, node_id: str) -> List[DiagramEdge]:
        """Return all edges pointing to *node_id*."""
        return [e for e in self.edges if e.target_id == node_id]

    def node_ids(self) -> Set[str]:
        """Return the set of all node ids."""
        return {n.id for n in self.nodes}
