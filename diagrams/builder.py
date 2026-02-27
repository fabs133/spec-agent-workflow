"""Build Diagram objects from raw extractor data.

Each ``build_*`` function takes a dict (as returned by the corresponding
extractor function) and produces a fully-populated :class:`Diagram`.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List

from diagrams.models import Diagram, DiagramEdge, DiagramNode


def _is_trivial_init(file_path: str, project_root: str = ".") -> bool:
    """Return True if the file is an ``__init__.py`` with no meaningful code."""
    fp = Path(project_root) / file_path
    if not fp.exists():
        return True
    try:
        source = fp.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return True
    if not source.strip():
        return True
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return True
    # Only a module docstring and possibly imports → trivial
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, (ast.Constant, ast.Str)):
            continue  # docstring
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        return False
    return True


def build_component_diagram(module_data: Dict[str, Any], project_root: str = ".") -> Diagram:
    """Build a component diagram from module graph data.

    Creates boundary nodes for packages, module nodes for files, and
    import edges between modules.
    """
    nodes: List[DiagramNode] = []
    edges: List[DiagramEdge] = []

    # Group modules by package
    packages: Dict[str, List[Dict]] = {}
    for mod in module_data.get("modules", []):
        pkg = mod["name"].split(".")[0]
        packages.setdefault(pkg, []).append(mod)

    # Create boundary + module nodes
    for pkg_name, mods in sorted(packages.items()):
        boundary_id = f"pkg_{pkg_name}"
        nodes.append(DiagramNode(
            id=boundary_id,
            label=pkg_name,
            node_type="boundary",
        ))

        for mod in mods:
            # Skip trivial __init__.py
            if mod["name"].endswith(".__init__"):
                if _is_trivial_init(mod["file"], project_root):
                    continue

            short_label = mod["name"].split(".")[-1]
            nodes.append(DiagramNode(
                id=mod["name"],
                label=short_label,
                node_type="module",
                parent_id=boundary_id,
                metadata={
                    "docstring": mod.get("docstring", ""),
                    "classes": mod.get("classes", []),
                    "functions": mod.get("functions", []),
                },
            ))

    node_ids = {n.id for n in nodes}

    # Create edges for imports
    edge_idx = 0
    seen_edges = set()
    for imp in module_data.get("imports", []):
        src = imp["from"]
        tgt = imp["to"]
        if src not in node_ids or tgt not in node_ids:
            continue
        pair = (src, tgt)
        if pair in seen_edges:
            continue
        seen_edges.add(pair)

        # Cross-package imports are dashed
        src_pkg = src.split(".")[0]
        tgt_pkg = tgt.split(".")[0]
        edge_type = "dashed" if src_pkg != tgt_pkg else "solid"

        edges.append(DiagramEdge(
            id=f"imp_{edge_idx}",
            source_id=src,
            target_id=tgt,
            label="imports",
            edge_type=edge_type,
        ))
        edge_idx += 1

    return Diagram(
        title="Komponentendiagramm",
        diagram_type="component",
        nodes=nodes,
        edges=edges,
    )


def build_state_diagram(workflow_data: Dict[str, Any]) -> Diagram:
    """Build a state diagram from manifest workflow data.

    Creates initial/final pseudo-states plus one state node per
    workflow step, connected by transition edges.
    """
    nodes: List[DiagramNode] = []
    edges: List[DiagramEdge] = []

    # Initial node
    nodes.append(DiagramNode(
        id="__initial__",
        label="",
        node_type="initial",
        width=30,
        height=30,
    ))

    # State nodes
    for state in workflow_data.get("states", []):
        nodes.append(DiagramNode(
            id=state["name"],
            label=state["name"],
            node_type="state",
            metadata={
                "agent": state.get("agent", ""),
                "specs": state.get("specs", {}),
                "retry_max": state.get("retry_max", 1),
            },
        ))

    # Final node
    nodes.append(DiagramNode(
        id="__final__",
        label="",
        node_type="final",
        width=30,
        height=30,
    ))

    edge_idx = 0

    # Edge: initial → entry_step
    entry = workflow_data.get("entry_step", "")
    if entry:
        edges.append(DiagramEdge(
            id=f"tr_{edge_idx}",
            source_id="__initial__",
            target_id=entry,
            edge_type="transition",
        ))
        edge_idx += 1

    # Edges from transitions
    state_names = {s["name"] for s in workflow_data.get("states", [])}
    last_target = ""
    for tr in workflow_data.get("transitions", []):
        label = tr.get("condition", "on_pass")
        edges.append(DiagramEdge(
            id=f"tr_{edge_idx}",
            source_id=tr["from"],
            target_id=tr["to"],
            label=label,
            edge_type="transition",
        ))
        edge_idx += 1
        last_target = tr["to"]

    # Edge: last state → final
    if last_target:
        edges.append(DiagramEdge(
            id=f"tr_{edge_idx}",
            source_id=last_target,
            target_id="__final__",
            label="on_pass",
            edge_type="transition",
        ))
        edge_idx += 1

    # Retry self-loops
    for state in workflow_data.get("states", []):
        retry_max = state.get("retry_max", 1)
        if retry_max > 1:
            edges.append(DiagramEdge(
                id=f"tr_{edge_idx}",
                source_id=state["name"],
                target_id=state["name"],
                label="retry",
                edge_type="transition_fail",
            ))
            edge_idx += 1

    return Diagram(
        title="Zustandsdiagramm \u2014 Workflow Pipeline",
        diagram_type="state",
        nodes=nodes,
        edges=edges,
    )


def build_usecase_diagram(usecase_data: Dict[str, Any]) -> Diagram:
    """Build a use-case diagram from use-case data.

    Creates a system boundary, actor nodes outside it, use-case ellipses
    inside it, and association edges.
    """
    nodes: List[DiagramNode] = []
    edges: List[DiagramEdge] = []

    # System boundary
    system_name = usecase_data.get("system_name", "System")
    boundary_id = "system_boundary"
    nodes.append(DiagramNode(
        id=boundary_id,
        label=system_name,
        node_type="boundary",
    ))

    # Actor nodes (outside boundary)
    for actor in usecase_data.get("actors", []):
        nodes.append(DiagramNode(
            id=actor["id"],
            label=actor["name"],
            node_type="actor",
            width=40,
            height=60,
        ))

    # Use-case nodes (inside boundary)
    for uc in usecase_data.get("usecases", []):
        nodes.append(DiagramNode(
            id=uc["id"],
            label=uc["name"],
            node_type="usecase",
            parent_id=boundary_id,
            width=200,
            height=50,
        ))

    # Association edges
    edge_idx = 0
    for assoc in usecase_data.get("associations", []):
        edges.append(DiagramEdge(
            id=f"assoc_{edge_idx}",
            source_id=assoc["actor"],
            target_id=assoc["usecase"],
            edge_type="association",
        ))
        edge_idx += 1

    return Diagram(
        title="Use-Case-Diagramm",
        diagram_type="usecase",
        nodes=nodes,
        edges=edges,
    )
