"""Execution history tracking for pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionRecord:
    """A single pipeline execution record.

    Parameters
    ----------
    pipeline_name : str
        Name of the pipeline that was executed.
    status : str
        One of: "running", "completed", "failed", "cancelled".
    started_at : datetime
        When execution began.
    finished_at : datetime, optional
        When execution finished (None if still running).
    inputs : dict
        Input variables supplied to the pipeline.
    outputs : dict
        Output variables produced by the pipeline.
    error : str, optional
        Error message if the pipeline failed.
    """

    pipeline_name: str
    status: str = "running"
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize record to a dictionary."""
        return {
            "pipeline_name": self.pipeline_name,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "error": self.error,
        }


class ExecutionHistory:
    """In-memory store of pipeline execution records.

    Provides query methods for inspecting past runs.

    Examples
    --------
    >>> history = ExecutionHistory()
    >>> record = history.start("etl", inputs={"source": "s3://bucket"})
    >>> history.complete(record, outputs={"rows": 1000})
    >>> len(history.list_recent(limit=5))
    1
    """

    def __init__(self) -> None:
        self._records: List[ExecutionRecord] = []

    def start(self, pipeline_name: str, inputs: Optional[Dict[str, Any]] = None) -> ExecutionRecord:
        """Record the start of a pipeline execution.

        Parameters
        ----------
        pipeline_name : str
            Name of the pipeline being executed.
        inputs : dict, optional
            Input variables supplied.

        Returns
        -------
        ExecutionRecord
            The newly created record.
        """
        record = ExecutionRecord(
            pipeline_name=pipeline_name,
            status="running",
            inputs=inputs or {},
        )
        self._records.append(record)
        return record

    def complete(self, record: ExecutionRecord, outputs: Dict[str, Any]) -> None:
        """Mark a pipeline execution as completed.

        Parameters
        ----------
        record : ExecutionRecord
            The record returned by :meth:`start`.
        outputs : dict
            Final outputs from the pipeline.
        """
        record.status = "completed"
        record.finished_at = datetime.now(timezone.utc)
        record.outputs = outputs

    def fail(self, record: ExecutionRecord, error: str) -> None:
        """Mark a pipeline execution as failed.

        Parameters
        ----------
        record : ExecutionRecord
            The record returned by :meth:`start`.
        error : str
            Error description.
        """
        record.status = "failed"
        record.finished_at = datetime.now(timezone.utc)
        record.error = error

    def cancel(self, record: ExecutionRecord) -> None:
        """Mark a pipeline execution as cancelled.

        Parameters
        ----------
        record : ExecutionRecord
            The record returned by :meth:`start`.
        """
        record.status = "cancelled"
        record.finished_at = datetime.now(timezone.utc)

    def list_recent(self, limit: int = 10) -> List[ExecutionRecord]:
        """Return the most recent execution records.

        Parameters
        ----------
        limit : int
            Maximum number of records to return (default: 10).

        Returns
        -------
        list of ExecutionRecord
            Most recent first.
        """
        return list(reversed(self._records[-limit:]))

    def find_by_pipeline(self, pipeline_name: str) -> List[ExecutionRecord]:
        """Return all records for a given pipeline.

        Parameters
        ----------
        pipeline_name : str
            Pipeline name to filter by.

        Returns
        -------
        list of ExecutionRecord
            Matching records, most recent first.
        """
        return [r for r in reversed(self._records) if r.pipeline_name == pipeline_name]

    def count(self) -> int:
        """Return total number of executions recorded."""
        return len(self._records)
