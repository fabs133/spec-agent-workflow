"""Extract project data for diagram generation.

Each function reads from the filesystem and returns a plain dict.
No Diagram objects are created here — that is the builder's job.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Dict, List, Set

# Packages within the project that we consider "internal"
_INTERNAL_PACKAGES = {"core", "agents", "db", "diagrams"}


def _module_name_from_path(file_path: Path, project_root: Path) -> str:
    """Convert a file path to a dotted module name.

    Example: core/specs.py → "core.specs"
    """
    rel = file_path.relative_to(project_root)
    parts = list(rel.with_suffix("").parts)
    return ".".join(parts)


def _is_internal_import(module_name: str) -> bool:
    """Return True if *module_name* belongs to one of the project packages."""
    top = module_name.split(".")[0]
    return top in _INTERNAL_PACKAGES


def extract_module_graph(project_root: Path) -> Dict[str, Any]:
    """Parse Python modules and their import relationships via ``ast``.

    Scans the directories listed in ``_INTERNAL_PACKAGES`` for ``.py`` files,
    extracts module-level metadata (docstring, classes, functions) and
    internal import edges.

    Returns a dict with keys ``modules`` and ``imports``.
    """
    project_root = Path(project_root)
    modules: List[Dict[str, Any]] = []
    imports: List[Dict[str, Any]] = []
    known_modules: Set[str] = set()

    # Collect all .py files in internal packages
    py_files: List[Path] = []
    for pkg in _INTERNAL_PACKAGES:
        pkg_dir = project_root / pkg
        if pkg_dir.is_dir():
            py_files.extend(sorted(pkg_dir.glob("*.py")))

    # First pass: register known module names
    for fp in py_files:
        known_modules.add(_module_name_from_path(fp, project_root))

    # Second pass: parse each file
    for fp in py_files:
        mod_name = _module_name_from_path(fp, project_root)
        try:
            source = fp.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(fp))
        except (SyntaxError, UnicodeDecodeError):
            continue

        docstring = ast.get_docstring(tree) or ""
        classes: List[str] = []
        functions: List[str] = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                functions.append(node.name)

        modules.append({
            "name": mod_name,
            "docstring": docstring,
            "classes": classes,
            "functions": functions,
            "file": str(fp.relative_to(project_root)),
        })

        # Extract imports pointing to internal modules
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                target_module = node.module
                if _is_internal_import(target_module):
                    # Resolve target to a known module if possible
                    resolved = target_module
                    if resolved not in known_modules:
                        # e.g. "core" might resolve to "core.__init__"
                        candidate = resolved + ".__init__"
                        if candidate in known_modules:
                            resolved = candidate
                    names = [alias.name for alias in node.names]
                    imports.append({
                        "from": mod_name,
                        "to": resolved,
                        "names": names,
                    })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_internal_import(alias.name):
                        imports.append({
                            "from": mod_name,
                            "to": alias.name,
                            "names": [alias.name],
                        })

    return {"modules": modules, "imports": imports}


def extract_workflow_states(manifest_path: Path) -> Dict[str, Any]:
    """Read a manifest JSON and extract the workflow as a state graph.

    Returns a dict with ``states``, ``transitions``, ``entry_step``, and
    ``budgets``.
    """
    manifest_path = Path(manifest_path)
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))

    states: List[Dict[str, Any]] = []
    for name, step in raw.get("steps", {}).items():
        states.append({
            "name": name,
            "agent": step.get("agent", ""),
            "specs": step.get("specs", {}),
            "retry_max": step.get("retry", {}).get("max_attempts", 1),
        })

    transitions: List[Dict[str, Any]] = []
    for edge in raw.get("edges", []):
        transitions.append({
            "from": edge["from"],
            "to": edge["to"],
            "condition": edge.get("condition", "on_pass"),
        })

    return {
        "states": states,
        "transitions": transitions,
        "entry_step": raw.get("entry_step", ""),
        "budgets": raw.get("budgets", {}),
    }


def extract_usecases(project_root: Path) -> Dict[str, Any]:
    """Load use-case data from ``diagrams/usecase_data.json``.

    Falls back to hard-coded data if the file does not exist.
    """
    project_root = Path(project_root)
    uc_path = project_root / "diagrams" / "usecase_data.json"
    if uc_path.exists():
        return json.loads(uc_path.read_text(encoding="utf-8"))

    # Fallback data matching the project's use-case diagram
    return {
        "system_name": "Text- & Kanban-Workflow-System",
        "actors": [
            {"id": "projektplaner", "name": "Projektplaner"},
            {"id": "teamleiter", "name": "Teamleiter"},
            {"id": "admin", "name": "Administrator"},
        ],
        "usecases": [
            {"id": "uc1", "name": "Textdateien einlesen"},
            {"id": "uc2", "name": "Inhalte zusammenfassen"},
            {"id": "uc3", "name": "Work Items f\u00fcr Kanban erzeugen"},
            {"id": "uc4", "name": "Workflow & Modell konfigurieren"},
            {"id": "uc5", "name": "Ergebnisse & Historie einsehen"},
            {"id": "uc6", "name": "Anwendung installieren & konfigurieren"},
            {"id": "uc7", "name": "Projektstatus f\u00fcr Pr\u00e4sentation vorbereiten"},
        ],
        "associations": [
            {"actor": "projektplaner", "usecase": "uc1"},
            {"actor": "projektplaner", "usecase": "uc2"},
            {"actor": "projektplaner", "usecase": "uc3"},
            {"actor": "projektplaner", "usecase": "uc5"},
            {"actor": "projektplaner", "usecase": "uc7"},
            {"actor": "teamleiter", "usecase": "uc2"},
            {"actor": "teamleiter", "usecase": "uc3"},
            {"actor": "teamleiter", "usecase": "uc5"},
            {"actor": "teamleiter", "usecase": "uc7"},
            {"actor": "admin", "usecase": "uc4"},
            {"actor": "admin", "usecase": "uc5"},
            {"actor": "admin", "usecase": "uc6"},
        ],
    }
