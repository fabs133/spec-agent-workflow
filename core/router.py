"""Router: selects the next step based on edge conditions and step outcomes.

The graph structure comes from the manifest (edges), NOT from specs.
Specs only determine pass/fail; the router uses that to pick the next edge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Edge:
    """A directed edge in the workflow graph."""
    from_step: str
    to_step: str
    condition: str = "on_pass"  # "on_pass" | "on_fail" | "always"


class Router:
    """Selects the next step based on the current step outcome and graph edges."""

    def __init__(self, edges: List[Edge]):
        self.edges = edges

    def next_step(self, current_step: str, step_passed: bool) -> Optional[str]:
        """Given a step result, find the next step to execute.

        Returns None if no matching edge exists (workflow ends).
        Returns "__end__" for explicit terminal edges.
        """
        condition = "on_pass" if step_passed else "on_fail"
        for edge in self.edges:
            if edge.from_step == current_step:
                if edge.condition == condition or edge.condition == "always":
                    return edge.to_step
        return None

    def get_all_edges_from(self, step_name: str) -> List[Edge]:
        """Get all outgoing edges from a step (useful for visualization)."""
        return [e for e in self.edges if e.from_step == step_name]

    def get_step_names(self) -> List[str]:
        """Get all unique step names referenced in edges."""
        names = set()
        for edge in self.edges:
            names.add(edge.from_step)
            if edge.to_step != "__end__":
                names.add(edge.to_step)
        return sorted(names)
