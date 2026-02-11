"""Step definition: binds an agent to its specs and retry policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RetryPolicy:
    """How many times a step can be retried and with what delay."""
    max_attempts: int = 2
    delay_seconds: float = 1.0


@dataclass
class StepDefinition:
    """A step in the workflow graph.

    Binds an agent to its spec functions and retry policy.
    Loaded from the manifest YAML.
    """
    name: str
    agent_name: str
    pre_specs: List[str] = field(default_factory=list)
    post_specs: List[str] = field(default_factory=list)
    invariant_specs: List[str] = field(default_factory=list)
    retry: RetryPolicy = field(default_factory=RetryPolicy)
