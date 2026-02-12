"""Manifest loader: reads JSON workflow definitions into in-memory objects.

The manifest is the source of truth:
- Defines agents, steps, specs, edges, budgets
- The graph structure is DATA, not code
- Swapping manifests = swapping workflows without changing Python code
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from core.errors import ManifestError
from core.router import Edge
from core.steps import RetryPolicy, StepDefinition


@dataclass
class Manifest:
    """Parsed workflow manifest."""
    name: str
    description: str
    version: str
    entry_step: str
    steps: Dict[str, StepDefinition]
    edges: List[Edge]
    defaults: Dict[str, Any] = field(default_factory=dict)
    budgets: Dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: str | Path) -> Manifest:
        """Load a manifest from a JSON file."""
        path = Path(path)
        if not path.exists():
            raise ManifestError(f"Manifest file not found: {path}")

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ManifestError(f"Invalid JSON in {path}: {e}")

        if not isinstance(raw, dict):
            raise ManifestError(f"Manifest must be a JSON object, got {type(raw)}")

        return cls._parse(raw)

    @classmethod
    def from_yaml(cls, path: str | Path) -> Manifest:
        """Backward-compatible alias for from_file."""
        return cls.from_file(path)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> Manifest:
        """Load a manifest from a dictionary (useful for testing)."""
        return cls._parse(raw)

    @classmethod
    def _parse(cls, raw: Dict[str, Any]) -> Manifest:
        """Parse a raw dictionary into a Manifest object."""
        # Required fields
        name = raw.get("name")
        if not name:
            raise ManifestError("Manifest must have a 'name' field")

        entry_step = raw.get("entry_step")
        if not entry_step:
            raise ManifestError("Manifest must have an 'entry_step' field")

        # Parse steps
        raw_steps = raw.get("steps", {})
        if not raw_steps:
            raise ManifestError("Manifest must define at least one step")

        steps = {}
        for step_name, step_data in raw_steps.items():
            if not isinstance(step_data, dict):
                raise ManifestError(f"Step '{step_name}' must be a mapping")

            agent_name = step_data.get("agent")
            if not agent_name:
                raise ManifestError(f"Step '{step_name}' must have an 'agent' field")

            specs = step_data.get("specs", {})
            retry_data = step_data.get("retry", {})

            steps[step_name] = StepDefinition(
                name=step_name,
                agent_name=agent_name,
                pre_specs=specs.get("pre", []),
                post_specs=specs.get("post", []),
                invariant_specs=specs.get("invariant", []),
                retry=RetryPolicy(
                    max_attempts=retry_data.get("max_attempts", 2),
                    delay_seconds=retry_data.get("delay_seconds", 1.0),
                ),
            )

        # Validate entry_step exists
        if entry_step not in steps:
            raise ManifestError(
                f"entry_step '{entry_step}' not found in steps: {list(steps.keys())}"
            )

        # Parse edges
        raw_edges = raw.get("edges", [])
        edges = []
        for edge_data in raw_edges:
            if not isinstance(edge_data, dict):
                raise ManifestError(f"Each edge must be a mapping, got {type(edge_data)}")
            edges.append(Edge(
                from_step=edge_data["from"],
                to_step=edge_data["to"],
                condition=edge_data.get("condition", "on_pass"),
            ))

        return cls(
            name=name,
            description=raw.get("description", ""),
            version=raw.get("version", "1.0"),
            entry_step=entry_step,
            steps=steps,
            edges=edges,
            defaults=raw.get("defaults", {}),
            budgets=raw.get("budgets", {}),
        )
