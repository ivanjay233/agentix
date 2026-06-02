"""Progress bar rendering for pipeline execution using Rich."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

console = Console()


class PipelineProgress:
    """Manage a Rich progress display for pipeline stage execution.

    Parameters
    ----------
    stage_names : list of str
        Names of pipeline stages in execution order.
    transient : bool
        If True, the progress display disappears after completion (default: True).

    Examples
    --------
    >>> pp = PipelineProgress(["extract", "transform", "load"])
    >>> with pp:
    ...     pp.advance("extract")
    ...     pp.advance("transform")
    ...     pp.advance("load")
    """

    def __init__(self, stage_names: List[str], transient: bool = True) -> None:
        self._stage_names = stage_names
        self._transient = transient
        self._progress: Optional[Progress] = None
        self._tasks: Dict[str, int] = {}
        self._total_stages = len(stage_names)

    def __enter__(self) -> "PipelineProgress":
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            transient=self._transient,
            console=console,
        )
        self._progress.__enter__()
        return self

    def __exit__(self, *args: Any) -> None:
        if self._progress:
            self._progress.__exit__(*args)
            self._progress = None

    def advance(self, stage_name: str) -> None:
        """Mark a stage as completed and advance the progress bar.

        Parameters
        ----------
        stage_name : str
            Name of the completed stage.
        """
        if self._progress is None:
            return

        idx = self._stage_names.index(stage_name) if stage_name in self._stage_names else -1
        task_id = self._progress.add_task(
            f"[cyan]{stage_name}[/cyan]",
            total=100,
        )
        self._progress.update(task_id, completed=100, description=f"[green]✓ {stage_name}[/green]")
        self._tasks[stage_name] = task_id
