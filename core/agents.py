"""Agent base class and registry.

Agents transform context into output. They:
- Accept a Context
- Perform their task (IO allowed: file reads, LLM calls, etc.)
- Return a modified Context (new data keys populated)
- Do NOT decide what runs next (that is the router's job)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Type

from core.models import Context


class BaseAgent(ABC):
    """Base class for all workflow agents."""

    name: str = "base"

    @abstractmethod
    async def execute(self, context: Context) -> Context:
        """Execute this agent's task and return updated context."""
        ...


# Agent registry: name -> class
_AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {}


def register_agent(name: str):
    """Decorator to register an agent class by name."""
    def decorator(cls: Type[BaseAgent]):
        _AGENT_REGISTRY[name] = cls
        cls.name = name
        return cls
    return decorator


def get_agent(name: str) -> BaseAgent:
    """Instantiate a registered agent by name."""
    cls = _AGENT_REGISTRY.get(name)
    if not cls:
        available = list(_AGENT_REGISTRY.keys())
        raise ValueError(f"Unknown agent: '{name}'. Available: {available}")
    return cls()


def list_agents() -> list[str]:
    """List all registered agent names."""
    return list(_AGENT_REGISTRY.keys())
