"""Board management — high-level operations on Kanban boards."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agentix.kanban import KanbanBoard, Task, TaskStatus
from agentix.priority import Priority


class BoardManager:
    """High-level board operations for pipeline execution tracking.

    Provides convenience methods over the raw KanbanBoard for common
    pipeline management scenarios.

    Parameters
    ----------
    board : KanbanBoard
        The board to manage.

    Examples
    --------
    >>> board = KanbanBoard("sprint")
    >>> mgr = BoardManager(board)
    >>> mgr.create_task("t1", "Write tests", "test", "codex")
    >>> mgr.start_task("t1")
    >>> mgr.complete_task("t1", {"test_count": 42})
    >>> mgr.task_count()
    1
    """

    def __init__(self, board: KanbanBoard) -> None:
        self.board = board

    def create_task(
        self,
        task_id: str,
        title: str,
        stage: str = "",
        agent: str = "",
        priority: Priority = Priority.MEDIUM,
    ) -> Task:
        """Create and add a new task to the board.

        Parameters
        ----------
        task_id : str
            Unique task identifier.
        title : str
            Human-readable task title.
        stage : str, optional
            Pipeline stage name.
        agent : str, optional
            Agent type assigned.
        priority : Priority, optional
            Task priority level.

        Returns
        -------
        Task
            The newly created task.
        """
        task = Task(id=task_id, title=title, stage=stage, agent=agent, priority=priority)
        self.board.add_task(task)
        return task

    def start_task(self, task_id: str) -> Task:
        """Move a task to in_progress.

        Parameters
        ----------
        task_id : str
            Identifier of the task to start.

        Returns
        -------
        Task
            The updated task.
        """
        task = self.board._find_task(task_id)
        task.update_status(TaskStatus.IN_PROGRESS)
        self.board.move_task(task_id, "in_progress")
        return task

    def review_task(self, task_id: str) -> Task:
        """Move a task to review.

        Parameters
        ----------
        task_id : str
            Identifier of the task to send to review.

        Returns
        -------
        Task
            The updated task.
        """
        task = self.board._find_task(task_id)
        task.update_status(TaskStatus.REVIEW)
        self.board.move_task(task_id, "review")
        return task

    def complete_task(self, task_id: str, artifacts: Any = None) -> Task:
        """Mark a task as done.

        Parameters
        ----------
        task_id : str
            Identifier of the task to complete.
        artifacts : Any, optional
            Output data produced.

        Returns
        -------
        Task
            The completed task.
        """
        task = self.board._find_task(task_id)
        task.update_status(TaskStatus.DONE)
        task.artifacts = artifacts
        self.board.move_task(task_id, "done")
        return task

    def task_count(self) -> int:
        """Return total number of tasks across all columns.

        Returns
        -------
        int
            Total task count.
        """
        return sum(self.board.column_size(c) for c in self.board.VALID_COLUMNS)

    def summary(self) -> Dict[str, int]:
        """Return a summary of task counts per column.

        Returns
        -------
        dict of str -> int
            Column name to task count.
        """
        return {col: self.board.column_size(col) for col in self.board.VALID_COLUMNS}

    def get_tasks_in_column(self, column: str) -> List[Dict[str, Any]]:
        """Return serialized tasks in a specific column.

        Parameters
        ----------
        column : str
            Column name.

        Returns
        -------
        list of dict
            Serialized task dicts.
        """
        state = self.board.get_board_state()
        return state.get(column, [])

    def get_stats(self) -> Dict[str, Any]:
        """Return statistics about the board.

        Returns
        -------
        dict
            Board statistics including total, per-column counts,
            and agent distribution.
        """
        state = self.board.get_board_state()
        all_tasks = self.board._all_tasks()

        agent_counts: Dict[str, int] = {}
        for task in all_tasks.values():
            agent_counts[task.agent] = agent_counts.get(task.agent, 0) + 1

        priority_counts: Dict[str, int] = {}
        for task in all_tasks.values():
            pname = task.priority.name
            priority_counts[pname] = priority_counts.get(pname, 0) + 1

        return {
            "board_name": self.board.name,
            "total_tasks": len(all_tasks),
            "per_column": {
                col: len(state.get(col, [])) for col in self.board.VALID_COLUMNS
            },
            "by_agent": agent_counts,
            "by_priority": priority_counts,
        }
