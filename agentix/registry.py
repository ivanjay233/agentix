"""Agent registry with hot-reload support for custom agent classes."""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from typing import Any, Dict, Optional, Set, Type

from agentix.agents.base import BaseAgent

logger = logging.getLogger("agentix")


class AgentRegistry:
    """Registry that discovers, stores, and hot-reloads agent classes.

    Agents are discovered automatically from the ``agentix.agents``
    package and can be registered manually via :meth:`register`.

    Parameters
    ----------
    auto_discover : bool
        If True (default), scan the agents package on init.

    Examples
    --------
    >>> registry = AgentRegistry()
    >>> registry.list_agents()
    ['CodexAgent', 'ReviewAgent']
    >>> cls = registry.get("CodexAgent")
    >>> cls.__name__
    'CodexAgent'
    """

    def __init__(self, auto_discover: bool = True) -> None:
        self._agents: Dict[str, Type[BaseAgent]] = {}
        self._modules: Set[str] = set()

        if auto_discover:
            self.discover()

    def discover(self) -> None:
        """Scan the ``agentix.agents`` package for BaseAgent subclasses."""
        import agentix.agents as agents_pkg

        prefix = agents_pkg.__name__ + "."
        for importer, modname, is_pkg in pkgutil.walk_packages(
            agents_pkg.__path__, prefix=prefix, onerror=lambda x: None
        ):
            if is_pkg:
                continue
            try:
                module = importlib.import_module(modname)
                self._modules.add(modname)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, BaseAgent)
                        and obj is not BaseAgent
                        and not inspect.isabstract(obj)
                    ):
                        self._agents[name] = obj
                        logger.debug("Discovered agent '%s' from %s", name, modname)
            except Exception as exc:
                logger.warning("Failed to load module '%s': %s", modname, exc)

    def register(self, agent_class: Type[BaseAgent], name: Optional[str] = None) -> None:
        """Register an agent class manually.

        Parameters
        ----------
        agent_class : type
            A concrete subclass of BaseAgent.
        name : str, optional
            Override key name (defaults to class name).
        """
        key = name or agent_class.__name__
        self._agents[key] = agent_class
        logger.info("Registered agent '%s'", key)

    def get(self, name: str) -> Type[BaseAgent]:
        """Retrieve an agent class by name.

        Parameters
        ----------
        name : str
            Agent class name.

        Returns
        -------
        type
            The agent class.

        Raises
        ------
        KeyError
            If no agent with ``name`` is registered.
        """
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not found in registry. Available: {', '.join(self.list_agents())}")
        return self._agents[name]

    def list_agents(self) -> list:
        """Return sorted list of registered agent names."""
        return sorted(self._agents.keys())

    def hot_reload(self) -> int:
        """Reload all previously loaded modules and rediscover agents.

        Returns
        -------
        int
            Number of agents registered after reload.
        """
        # Reload discovered modules
        for modname in list(self._modules):
            try:
                module = importlib.import_module(modname)
                importlib.reload(module)
            except Exception as exc:
                logger.warning("Failed to reload '%s': %s", modname, exc)

        # Clear and rediscover
        self._agents.clear()
        self.discover()
        logger.info("Hot-reload complete — %d agents registered", len(self._agents))
        return len(self._agents)

    def remove(self, name: str) -> None:
        """Remove an agent from the registry.

        Parameters
        ----------
        name : str
            Name of the agent to remove.
        """
        self._agents.pop(name, None)
