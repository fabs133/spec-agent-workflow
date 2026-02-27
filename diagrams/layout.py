"""Deterministic layout algorithms for diagram positioning.

All positions are computed without randomness — identical input always
produces identical output.
"""

from __future__ import annotations

from diagrams.models import Diagram


def apply_layout(diagram: Diagram) -> Diagram:
    """Assign x/y coordinates to every node in *diagram* (in-place).

    The layout strategy depends on ``diagram.diagram_type``:

    * ``component`` — packages as columns, modules stacked vertically.
    * ``state`` — horizontal chain from initial to final.
    * ``usecase`` — actors on the left, use-cases inside a boundary.

    Returns the same diagram object.
    """
    if diagram.diagram_type == "component":
        _layout_component(diagram)
    elif diagram.diagram_type == "state":
        _layout_state(diagram)
    elif diagram.diagram_type == "usecase":
        _layout_usecase(diagram)
    return diagram


def _layout_component(diagram: Diagram) -> None:
    """Column-per-package layout."""
    # Group module nodes by their parent (boundary) id
    boundaries = [n for n in diagram.nodes if n.node_type == "boundary"]
    children: dict[str, list] = {b.id: [] for b in boundaries}
    for n in diagram.nodes:
        if n.parent_id and n.parent_id in children:
            children[n.parent_id].append(n)

    col_x = 60
    padding_x = 80
    padding_y = 40
    module_h = 60
    module_w = 160
    boundary_start_size = 30  # swimlane header height

    for boundary in boundaries:
        mods = children[boundary.id]
        num = len(mods)
        # Boundary size
        boundary.x = col_x
        boundary.y = 40
        boundary.width = module_w + 40  # 20px padding on each side
        boundary.height = boundary_start_size + num * (module_h + padding_y) + padding_y

        # Module positions inside boundary
        for i, mod in enumerate(mods):
            mod.x = col_x + 20
            mod.y = 40 + boundary_start_size + padding_y + i * (module_h + padding_y)
            mod.width = module_w
            mod.height = module_h

        col_x += boundary.width + padding_x


def _layout_state(diagram: Diagram) -> None:
    """Horizontal left-to-right layout for state diagrams."""
    initial = None
    final = None
    states = []
    for n in diagram.nodes:
        if n.node_type == "initial":
            initial = n
        elif n.node_type == "final":
            final = n
        elif n.node_type == "state":
            states.append(n)

    # Determine order from edges
    ordered = _topological_order_states(diagram, states)

    x = 60
    y = 120
    gap = 200

    if initial:
        initial.x = x
        initial.y = y + 15  # centre vertically with states
        x += gap // 2

    for state in ordered:
        state.x = x
        state.y = y
        state.width = 160
        state.height = 60
        x += gap

    if final:
        final.x = x
        final.y = y + 15


def _topological_order_states(diagram: Diagram, states: list) -> list:
    """Order state nodes following transition edges."""
    name_to_node = {n.id: n for n in states}
    # Build adjacency from transition edges (skip self-loops and initial/final)
    order_map: dict[str, str] = {}
    for e in diagram.edges:
        if e.source_id == e.target_id:
            continue
        if e.source_id.startswith("__") or e.target_id.startswith("__"):
            continue
        order_map[e.source_id] = e.target_id

    # Find the entry state (pointed to by __initial__)
    entry_id = None
    for e in diagram.edges:
        if e.source_id == "__initial__":
            entry_id = e.target_id
            break

    if not entry_id or entry_id not in name_to_node:
        return states  # fallback

    ordered = []
    visited = set()
    current = entry_id
    while current and current in name_to_node and current not in visited:
        ordered.append(name_to_node[current])
        visited.add(current)
        current = order_map.get(current)

    # Append any remaining states not in the chain
    for s in states:
        if s.id not in visited:
            ordered.append(s)

    return ordered


def _layout_usecase(diagram: Diagram) -> None:
    """Actors on the left, use-cases in a boundary grid on the right."""
    boundary = None
    actors = []
    usecases = []
    for n in diagram.nodes:
        if n.node_type == "boundary":
            boundary = n
        elif n.node_type == "actor":
            actors.append(n)
        elif n.node_type == "usecase":
            usecases.append(n)

    # Actors: column on the left
    actor_x = 40
    actor_y_start = 80
    actor_gap = 120
    for i, actor in enumerate(actors):
        actor.x = actor_x
        actor.y = actor_y_start + i * actor_gap
        actor.width = 40
        actor.height = 60

    # Boundary
    boundary_x = 200
    boundary_y = 40
    uc_w = 200
    uc_h = 50
    uc_padding_x = 40
    uc_padding_y = 30
    cols = 2
    boundary_start_size = 30

    rows = (len(usecases) + cols - 1) // cols
    if boundary:
        boundary.x = boundary_x
        boundary.y = boundary_y
        boundary.width = cols * (uc_w + uc_padding_x) + uc_padding_x
        boundary.height = boundary_start_size + rows * (uc_h + uc_padding_y) + uc_padding_y

    # Use-case positions in grid inside boundary
    for idx, uc in enumerate(usecases):
        col = idx % cols
        row = idx // cols
        uc.x = boundary_x + uc_padding_x + col * (uc_w + uc_padding_x)
        uc.y = boundary_y + boundary_start_size + uc_padding_y + row * (uc_h + uc_padding_y)
        uc.width = uc_w
        uc.height = uc_h
