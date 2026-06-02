"""Configuration models for pipelines and stages using dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StageConfig:
    """Configuration for a single pipeline stage.

    Parameters
    ----------
    name : str
        Unique identifier for this stage within the pipeline.
    agent_type : str
        Identifier of the agent class that handles this stage.
    input_keys : list of str, optional
        Context keys consumed by this stage.
    output_keys : list of str, optional
        Context keys produced by this stage.
    depends_on : list of str, optional
        Names of stages that must complete before this one runs.
    timeout : float, optional
        Maximum execution time in seconds (default: no timeout).
    retry_count : int, optional
        Number of retries on failure (default: 0).
    """

    name: str
    agent_type: str
    input_keys: List[str] = field(default_factory=list)
    output_keys: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    timeout: Optional[float] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a plain dict compatible with Pipeline stages."""
        d: Dict[str, Any] = {
            "name": self.name,
            "agent_type": self.agent_type,
            "input_keys": self.input_keys,
            "output_keys": self.output_keys,
            "depends_on": self.depends_on,
        }
        if self.timeout is not None:
            d["timeout"] = self.timeout
        if self.retry_count:
            d["retry_count"] = self.retry_count
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StageConfig":
        """Create from a dictionary."""
        return cls(
            name=d["name"],
            agent_type=d["agent_type"],
            input_keys=d.get("input_keys", []),
            output_keys=d.get("output_keys", []),
            depends_on=d.get("depends_on", []),
            timeout=d.get("timeout"),
            retry_count=d.get("retry_count", 0),
        )


@dataclass
class PipelineConfig:
    """Configuration for an entire pipeline.

    Parameters
    ----------
    name : str
        Human-readable pipeline identifier.
    stages : list of StageConfig, optional
        Stage definitions for the pipeline.
    max_concurrency : int, optional
        Maximum parallel stages when using concurrent execution (default: 4).
    """

    name: str
    stages: List[StageConfig] = field(default_factory=list)
    max_concurrency: int = 4

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a plain dict."""
        return {
            "name": self.name,
            "stages": [s.to_dict() for s in self.stages],
            "max_concurrency": self.max_concurrency,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PipelineConfig":
        """Create from a dictionary."""
        stages = [StageConfig.from_dict(s) for s in d.get("stages", [])]
        return cls(
            name=d["name"],
            stages=stages,
            max_concurrency=d.get("max_concurrency", 4),
        )
