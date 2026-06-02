"""
Pipeline — defines stages with dependencies, serialized to/from YAML.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import yaml


class Pipeline:
    """A pipeline represents a directed graph of processing stages.

    Each stage carries:
      - name         : unique identifier within the pipeline
      - agent_type   : which agent class handles this stage
      - input_keys   : context keys consumed by this stage
      - output_keys  : context keys produced by this stage
      - depends_on   : list of stage names that must complete first
    """

    def __init__(self, name: str, stages: Optional[List[Dict[str, Any]]] = None) -> None:
        self.name = name
        self.stages: List[Dict[str, Any]] = stages or []

    # ------------------------------------------------------------------
    # Stage management
    # ------------------------------------------------------------------

    def add_stage(
        self,
        name: str,
        agent_type: str,
        input_keys: Optional[List[str]] = None,
        output_keys: Optional[List[str]] = None,
        depends_on: Optional[List[str]] = None,
    ) -> None:
        """Append a new stage to this pipeline."""
        if self._find_stage(name) is not None:
            raise ValueError(f"A stage named '{name}' already exists in pipeline '{self.name}'.")

        stage: Dict[str, Any] = {
            "name": name,
            "agent_type": agent_type,
            "input_keys": input_keys or [],
            "output_keys": output_keys or [],
            "depends_on": depends_on or [],
        }
        self.stages.append(stage)

    def remove_stage(self, name: str) -> None:
        """Remove a stage by name."""
        stage = self._find_stage(name)
        if stage is None:
            raise KeyError(f"Stage '{name}' not found in pipeline '{self.name}'.")
        self.stages.remove(stage)

    def get_stage(self, name: str) -> Dict[str, Any]:
        """Retrieve a stage definition by name."""
        stage = self._find_stage(name)
        if stage is None:
            raise KeyError(f"Stage '{name}' not found in pipeline '{self.name}'.")
        return stage

    def _find_stage(self, name: str) -> Optional[Dict[str, Any]]:
        for s in self.stages:
            if s["name"] == name:
                return s
        return None

    # ------------------------------------------------------------------
    # Dependency helpers
    # ------------------------------------------------------------------

    def dependency_graph(self) -> Dict[str, List[str]]:
        """Return a mapping of stage -> list of stages it depends on."""
        return {s["name"]: list(s.get("depends_on", [])) for s in self.stages}

    def topological_sort(self) -> List[str]:
        """Return stage names in dependency order (topological sort)."""
        graph = self.dependency_graph()
        # in_degree[name] = how many stages must come before 'name'
        in_degree: Dict[str, int] = {name: len(deps) for name, deps in graph.items()}

        queue = [name for name, deg in in_degree.items() if deg == 0]
        ordered: List[str] = []

        while queue:
            node = queue.pop(0)
            ordered.append(node)
            # Find all stages that depend on 'node' and decrement their in_degree
            for name, deps in graph.items():
                if node in deps:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)

        # Check for cycles
        if len(ordered) != len(graph):
            raise RuntimeError(f"Cycle detected in pipeline '{self.name}'.")

        return ordered

    # ------------------------------------------------------------------
    # YAML serialisation
    # ------------------------------------------------------------------

    def to_yaml(self) -> str:
        """Serialize this pipeline to a YAML string."""
        data = {
            "name": self.name,
            "stages": self.stages,
        }
        return yaml.safe_dump(data, sort_keys=False, default_flow_style=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "Pipeline":
        """Deserialize a pipeline from a YAML string."""
        data = yaml.safe_load(yaml_str)
        if not isinstance(data, dict):
            raise ValueError("YAML root must be a mapping.")
        return cls(name=data.get("name", "unnamed"), stages=data.get("stages", []))

    @classmethod
    def from_yaml_file(cls, path: str) -> "Pipeline":
        """Load a pipeline from a YAML file on disk."""
        with open(path, "r") as fh:
            return cls.from_yaml(fh.read())

    # ------------------------------------------------------------------
    # Built-in
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Pipeline(name='{self.name}', stages={len(self.stages)})"
