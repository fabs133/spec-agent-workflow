"""Validate diagram graph consistency.

The single public function :func:`validate_diagram` returns a list of
human-readable error strings.  An empty list means the diagram is valid.
"""

from __future__ import annotations

from typing import List

from diagrams.models import Diagram


def validate_diagram(diagram: Diagram) -> List[str]:
    """Check a :class:`Diagram` for structural errors.

    Checks performed:
    a) No duplicate node IDs.
    b) All edge source/target IDs reference existing nodes.
    c) No orphan nodes (except boundary-type nodes).
    d) parent_id references an existing node (if set).
    e) At least one node present.
    f) All node IDs are non-empty.
    g) State diagrams must have exactly one initial and at least one final node.

    Returns an empty list when the diagram is valid.
    """
    errors: List[str] = []

    # (e) At least one node
    if not diagram.nodes:
        errors.append("Error: diagram has no nodes")
        return errors

    # (f) Non-empty IDs
    for node in diagram.nodes:
        if not node.id:
            errors.append("Error: node has empty id")

    # (a) Duplicate node IDs
    seen_ids = set()
    for node in diagram.nodes:
        if node.id in seen_ids:
            errors.append(f"Error: duplicate node id '{node.id}'")
        seen_ids.add(node.id)

    node_ids = diagram.node_ids()

    # (b) Edge references
    for edge in diagram.edges:
        if edge.source_id not in node_ids:
            errors.append(
                f"Error: edge '{edge.id}' references unknown source '{edge.source_id}'"
            )
        if edge.target_id not in node_ids:
            errors.append(
                f"Error: edge '{edge.id}' references unknown target '{edge.target_id}'"
            )

    # (c) Orphan nodes (no edges at all, excluding boundaries)
    referenced = set()
    for edge in diagram.edges:
        referenced.add(edge.source_id)
        referenced.add(edge.target_id)
    for node in diagram.nodes:
        if node.node_type == "boundary":
            continue
        # Nodes with a parent are inside a boundary — not orphans
        if node.parent_id:
            continue
        if node.id not in referenced:
            errors.append(
                f"Error: orphan node '{node.id}' is unreferenced by any edge"
            )

    # (d) parent_id validity
    for node in diagram.nodes:
        if node.parent_id and node.parent_id not in node_ids:
            errors.append(
                f"Error: node '{node.id}' references unknown parent '{node.parent_id}'"
            )

    # (g) State diagram specifics
    if diagram.diagram_type == "state":
        initial_count = sum(1 for n in diagram.nodes if n.node_type == "initial")
        final_count = sum(1 for n in diagram.nodes if n.node_type == "final")
        if initial_count != 1:
            errors.append(
                f"Error: state diagram must have exactly 1 initial node, found {initial_count}"
            )
        if final_count < 1:
            errors.append(
                "Error: state diagram must have at least 1 final node"
            )

    return errors
