"""Pipeline scheduler — handles topological ordering and stage scheduling."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Set, Tuple

from agentix.pipeline import Pipeline

logger = logging.getLogger("agentix")


class PipelineScheduler:
    """Schedules pipeline stages based on dependency resolution.

    Provides topological ordering and readiness checks for use
    in both sequential and concurrent execution modes.

    Parameters
    ----------
    pipeline : Pipeline
        The pipeline whose stages are to be scheduled.

    Examples
    --------
    >>> p = Pipeline("etl")
    >>> p.add_stage("extract", "reader", output_keys=["raw"])
    >>> p.add_stage("transform", "processor", input_keys=["raw"], depends_on=["extract"])
    >>> sched = PipelineScheduler(p)
    >>> sched.ordered_stages()
    ['extract', 'transform']
    >>> sched.ready_stages({"extract"})
    ['transform']
    """

    def __init__(self, pipeline: Pipeline) -> None:
        self.pipeline = pipeline
        self._order: List[str] = []
        self._compute_order()

    def _compute_order(self) -> None:
        """Compute topological ordering on init."""
        try:
            self._order = self.pipeline.topological_sort()
        except RuntimeError as exc:
            logger.error("Failed to compute schedule: %s", exc)
            self._order = [s["name"] for s in self.pipeline.stages]

    def ordered_stages(self) -> List[str]:
        """Return stages in topological (dependency) order.

        Returns
        -------
        list of str
            Stage names in execution order.
        """
        return list(self._order)

    def ready_stages(self, completed: Set[str]) -> List[str]:
        """Return stages whose dependencies are all satisfied.

        Parameters
        ----------
        completed : set of str
            Names of stages that have already completed.

        Returns
        -------
        list of str
            Names of stages ready to execute.
        """
        ready: List[str] = []
        for stage in self.pipeline.stages:
            name = stage["name"]
            if name in completed:
                continue
            deps = set(stage.get("depends_on", []))
            if deps.issubset(completed):
                ready.append(name)
        return ready

    def pending_stages(self, completed: Set[str]) -> List[str]:
        """Return stages that are not yet completed.

        Parameters
        ----------
        completed : set of str
            Names of completed stages.

        Returns
        -------
        list of str
            Names of pending stages.
        """
        return [s["name"] for s in self.pipeline.stages if s["name"] not in completed]

    def dependency_graph(self) -> Dict[str, List[str]]:
        """Return the raw dependency graph.

        Returns
        -------
        dict of str -> list of str
            Stage name to list of dependencies.
        """
        return self.pipeline.dependency_graph()

    def has_cycle(self) -> bool:
        """Check if the pipeline's dependency graph contains a cycle.

        Returns
        -------
        bool
            True if a cycle exists.
        """
        try:
            self.pipeline.topological_sort()
            return False
        except RuntimeError:
            return True

    def critical_path(self) -> int:
        """Return the length of the longest dependency chain.

        Uses simple longest-path estimate based on dependency depth.

        Returns
        -------
        int
            Number of stages on the critical path.
        """
        graph = self.dependency_graph()
        depth: Dict[str, int] = {}

        def _depth(name: str) -> int:
            if name in depth:
                return depth[name]
            deps = graph.get(name, [])
            if not deps:
                depth[name] = 1
                return 1
            max_dep = max(_depth(d) for d in deps) + 1
            depth[name] = max_dep
            return max_dep

        for stage in self.pipeline.stages:
            _depth(stage["name"])

        return max(depth.values()) if depth else 0

    def levels(self) -> List[List[str]]:
        """Return stages grouped by dependency depth (topological levels).

        Returns
        -------
        list of list of str
            Each inner list contains stages at the same dependency depth
            that can run in parallel.
        """
        graph = self.dependency_graph()
        in_degree: Dict[str, int] = {name: len(deps) for name, deps in graph.items()}

        levels: List[List[str]] = []
        current = [name for name, deg in in_degree.items() if deg == 0]

        while current:
            levels.append(sorted(current))
            next_level: List[str] = []
            for node in current:
                for name, deps in graph.items():
                    if node in deps:
                        in_degree[name] -= 1
                        if in_degree[name] == 0:
                            next_level.append(name)
            current = next_level

        return levels
