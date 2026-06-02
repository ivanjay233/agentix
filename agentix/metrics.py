"""Stage timing and duration metrics for pipeline execution."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class StageTiming:
    """Timing data for a single stage execution.

    Parameters
    ----------
    stage_name : str
        Name of the stage.
    agent_type : str
        Agent type that processed the stage.
    started_at : float
        Monotonic timestamp of when execution started.
    finished_at : float, optional
        Monotonic timestamp of when execution finished.
    status : str
        One of: "running", "completed", "failed".
    error : str, optional
        Error message if the stage failed.
    """

    stage_name: str
    agent_type: str = ""
    started_at: float = field(default_factory=time.monotonic)
    finished_at: Optional[float] = None
    status: str = "running"
    error: Optional[str] = None

    @property
    def duration(self) -> Optional[float]:
        """Return duration in seconds, or None if still running."""
        if self.finished_at is not None:
            return self.finished_at - self.started_at
        return None

    @property
    def duration_ms(self) -> Optional[float]:
        """Return duration in milliseconds."""
        d = self.duration
        return d * 1000.0 if d is not None else None

    def finish(self, status: str = "completed", error: Optional[str] = None) -> None:
        """Mark the stage as finished."""
        self.finished_at = time.monotonic()
        self.status = status
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "stage_name": self.stage_name,
            "agent_type": self.agent_type,
            "duration_seconds": self.duration,
            "status": self.status,
            "error": self.error,
        }


class StageMetrics:
    """Collector for stage timing metrics across pipeline executions.

    Examples
    --------
    >>> metrics = StageMetrics()
    >>> timing = metrics.start_stage("extract", "reader")
    >>> # ... execute stage ...
    >>> metrics.finish_stage(timing, "completed")
    >>> metrics.total_time()
    0.123
    >>> metrics.average_time()
    0.123
    """

    def __init__(self) -> None:
        self._records: List[StageTiming] = []

    def start_stage(self, stage_name: str, agent_type: str = "") -> StageTiming:
        """Record the start of a stage.

        Parameters
        ----------
        stage_name : str
            Name of the stage.
        agent_type : str, optional
            Agent type handling the stage.

        Returns
        -------
        StageTiming
            The new timing record.
        """
        timing = StageTiming(stage_name=stage_name, agent_type=agent_type)
        self._records.append(timing)
        return timing

    def finish_stage(
        self, timing: StageTiming, status: str = "completed", error: Optional[str] = None
    ) -> None:
        """Record the completion of a stage.

        Parameters
        ----------
        timing : StageTiming
            The timing record returned by :meth:`start_stage`.
        status : str, optional
            Final status ("completed" or "failed").
        error : str, optional
            Error message if failed.
        """
        timing.finish(status=status, error=error)

    def total_time(self) -> float:
        """Return total accumulated stage execution time in seconds."""
        return sum(r.duration for r in self._records if r.duration is not None)

    def average_time(self) -> Optional[float]:
        """Return average stage execution time in seconds."""
        durations = [r.duration for r in self._records if r.duration is not None]
        if not durations:
            return None
        return sum(durations) / len(durations)

    def count_by_status(self) -> Dict[str, int]:
        """Return count of stages grouped by status.

        Returns
        -------
        dict of str -> int
            Status to count mapping.
        """
        counts: Dict[str, int] = {}
        for r in self._records:
            counts[r.status] = counts.get(r.status, 0) + 1
        return counts

    def slowest_stages(self, n: int = 5) -> List[StageTiming]:
        """Return the n slowest stages.

        Parameters
        ----------
        n : int
            Number of stages to return (default: 5).

        Returns
        -------
        list of StageTiming
            Slowest stages first.
        """
        completed = [r for r in self._records if r.duration is not None]
        completed.sort(key=lambda r: r.duration or 0, reverse=True)
        return completed[:n]

    def fastest_stages(self, n: int = 5) -> List[StageTiming]:
        """Return the n fastest stages.

        Parameters
        ----------
        n : int
            Number of stages to return (default: 5).

        Returns
        -------
        list of StageTiming
            Fastest stages first.
        """
        completed = [r for r in self._records if r.duration is not None]
        completed.sort(key=lambda r: r.duration or 0)
        return completed[:n]

    def clear(self) -> None:
        """Reset all collected metrics."""
        self._records.clear()

    def report(self) -> Dict[str, Any]:
        """Generate a comprehensive metrics report.

        Returns
        -------
        dict
            Full metrics report.
        """
        return {
            "total_stages": len(self._records),
            "total_time": self.total_time(),
            "average_time": self.average_time(),
            "by_status": self.count_by_status(),
            "slowest": [r.to_dict() for r in self.slowest_stages(5)],
            "fastest": [r.to_dict() for r in self.fastest_stages(5)],
        }
