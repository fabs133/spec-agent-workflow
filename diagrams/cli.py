"""CLI entry-point for diagram generation.

Usage::

    python -m diagrams --type component --output data/output/diagrams/
    python -m diagrams --type all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

from diagrams.builder import (
    build_component_diagram,
    build_state_diagram,
    build_usecase_diagram,
)
from diagrams.extractor import (
    extract_module_graph,
    extract_usecases,
    extract_workflow_states,
)
from diagrams.layout import apply_layout
from diagrams.models import Diagram
from diagrams.renderer import render_drawio, save_drawio
from diagrams.validator import validate_diagram


def _generate_one(
    diagram_type: str,
    project_root: Path,
    output_dir: Path,
) -> Tuple[str, Path]:
    """Generate a single diagram, returning ``(type, output_path)``."""
    if diagram_type == "component":
        data = extract_module_graph(project_root)
        diagram = build_component_diagram(data, str(project_root))
    elif diagram_type == "state":
        manifest_path = project_root / "manifests" / "text_extraction.json"
        data = extract_workflow_states(manifest_path)
        diagram = build_state_diagram(data)
    elif diagram_type == "usecase":
        data = extract_usecases(project_root)
        diagram = build_usecase_diagram(data)
    else:
        raise ValueError(f"Unknown diagram type: {diagram_type}")

    # Validate
    errors = validate_diagram(diagram)
    if errors:
        for err in errors:
            print(f"  Warning: {err}", file=sys.stderr)

    # Layout + render + save
    apply_layout(diagram)
    xml = render_drawio(diagram)
    out_path = output_dir / f"{diagram_type}.drawio"
    save_drawio(xml, out_path)
    return diagram_type, out_path


def main(argv: List[str] | None = None) -> None:
    """Parse arguments and generate diagrams."""
    parser = argparse.ArgumentParser(
        prog="diagrams",
        description="Generate Draw.io diagrams from project source code.",
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=["component", "state", "usecase", "all"],
        help="Which diagram to generate.",
    )
    parser.add_argument(
        "--output",
        default="data/output/diagrams/",
        help="Output directory (default: data/output/diagrams/).",
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root directory (default: current directory).",
    )
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    output_dir = Path(args.output)

    types = ["component", "state", "usecase"] if args.type == "all" else [args.type]

    for t in types:
        _, path = _generate_one(t, project_root, output_dir)
        print(f"Generated: {path}")


if __name__ == "__main__":
    main()
