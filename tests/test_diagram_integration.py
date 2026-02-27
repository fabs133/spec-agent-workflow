"""End-to-end integration tests for diagram generation."""

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

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
from diagrams.renderer import render_drawio
from diagrams.validator import validate_diagram

PROJECT_ROOT = Path(__file__).parent.parent
MANIFEST_PATH = PROJECT_ROOT / "manifests" / "text_extraction.json"


class TestComponentDiagramE2E:
    def test_end_to_end(self):
        data = extract_module_graph(PROJECT_ROOT)
        diagram = build_component_diagram(data, str(PROJECT_ROOT))
        errors = validate_diagram(diagram)
        assert errors == [], f"Validation errors: {errors}"

        apply_layout(diagram)
        xml = render_drawio(diagram)

        # Valid XML
        tree = ET.fromstring(xml)
        assert tree.tag == "mxfile"

        # Contains expected labels
        assert "core" in xml
        assert "agents" in xml


class TestStateDiagramE2E:
    def test_end_to_end(self):
        data = extract_workflow_states(MANIFEST_PATH)
        diagram = build_state_diagram(data)
        errors = validate_diagram(diagram)
        assert errors == [], f"Validation errors: {errors}"

        apply_layout(diagram)
        xml = render_drawio(diagram)

        tree = ET.fromstring(xml)
        assert tree.tag == "mxfile"

        assert "intake" in xml
        assert "extract" in xml
        assert "write" in xml


class TestUsecaseDiagramE2E:
    def test_end_to_end(self):
        data = extract_usecases(PROJECT_ROOT)
        diagram = build_usecase_diagram(data)
        errors = validate_diagram(diagram)
        assert errors == [], f"Validation errors: {errors}"

        apply_layout(diagram)
        xml = render_drawio(diagram)

        tree = ET.fromstring(xml)
        assert tree.tag == "mxfile"

        assert "Projektplaner" in xml
        assert "Teamleiter" in xml
        assert "Administrator" in xml

        # All 7 use-case labels
        for uc in data["usecases"]:
            assert uc["name"] in xml or uc["name"].replace("&", "&amp;") in xml


class TestCliAllGeneratesFiles:
    def test_generates_three_files(self, tmp_path):
        result = subprocess.run(
            [
                sys.executable, "-m", "diagrams",
                "--type", "all",
                "--output", str(tmp_path),
                "--project-root", str(PROJECT_ROOT),
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        assert (tmp_path / "component.drawio").exists()
        assert (tmp_path / "state.drawio").exists()
        assert (tmp_path / "usecase.drawio").exists()

        # All files are valid XML
        for name in ("component", "state", "usecase"):
            content = (tmp_path / f"{name}.drawio").read_text()
            ET.fromstring(content)
