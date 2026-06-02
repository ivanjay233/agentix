"""
BaseAgent — abstract interface for all agentix agents.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseAgent(ABC):
    """Abstract base class for all agents.

    Subclasses must implement:
      - process(task)   : execute the agent's core logic
      - validate()      : verify the agent is correctly configured
      - report()        : produce a human-readable summary of outcomes
    """

    def __init__(self, name: str = "base_agent", config: Optional[Dict[str, Any]] = None) -> None:
        self.name: str = name
        self.config: Dict[str, Any] = config or {}

    @abstractmethod
    async def process(self, task: Any) -> Any:
        """Execute the agent on a given task and return results."""

    @abstractmethod
    def validate(self) -> bool:
        """Ensure the agent is ready to run (e.g. dependencies exist)."""

    @abstractmethod
    def report(self) -> str:
        """Return a human-readable summary of the agent's activity."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
