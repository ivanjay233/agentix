"""
KanbanBoard — columns: todo, in_progress, review, done.

Provides task tracking across four standard columns with
operations for add, move, remove, and query.  Each task
carries status, timestamps, and reference to its agent.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from agentix.priority import Priority


class TaskStatus(str, Enum):
    """Possible states for a task on the Kanban board.

    Transition flow:
        TODO -> IN_PROGRESS -> REVIEW -> DONE
    """

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


class Task:
    """A single unit of work tracked on the Kanban board.

    Parameters
    ----------
    id : str, optional
        Unique identifier (auto-generated as hex string if omitted).
    title : str
        Human-readable title describing the task.
    stage : str
        Pipeline stage name this task belongs to.
    agent : str
        Agent type assigned to this task.
    status : TaskStatus
        Current board column status (default: TODO).
    artifacts : Any, optional
        Output data produced when the task completes.

    Examples
    --------
    >>> t = Task(title="Write tests", stage="test", agent="codex")
    >>> t.status
    <TaskStatus.TODO: 'todo'>
    >>> t.update_status(TaskStatus.IN_PROGRESS)
    >>> t.status
    <TaskStatus.IN_PROGRESS: 'in_progress'>
    """

    def __init__(
        self,
        id: Optional[str] = None,
        title: str = "",
        stage: str = "",
        agent: str = "",
        status: TaskStatus = TaskStatus.TODO,
        priority: Priority = Priority.MEDIUM,
        artifacts: Any = None,
    ) -> None:
        self.id: str = id or uuid.uuid4().hex[:12]
        self.title: str = title
        self.stage: str = stage
        self.agent: str = agent
        self.status: TaskStatus = status
        self.priority: Priority = priority
        self.artifacts: Any = artifacts
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def update_status(self, new_status: TaskStatus) -> None:
        """Transition this task to a new status.

        Parameters
        ----------
        new_status : TaskStatus
            The target status to transition to.

        Notes
        -----
        Does NOT validate transition legality (e.g. skipping columns).
        Callers should implement their own guards if needed.
        """
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict (for display / export).

        Returns
        -------
        dict
            Contains keys: id, title, stage, agent, status, priority, created_at, updated_at.
        """
        return {
            "id": self.id,
            "title": self.title,
            "stage": self.stage,
            "agent": self.agent,
            "status": self.status.value,
            "priority": self.priority.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"Task(id={self.id!r}, title={self.title!r}, status={self.status.value})"


class KanbanBoard:
    """A Kanban board with the classic columns.

    Columns
    -------
    todo, in_progress, review, done

    Parameters
    ----------
    name : str
        Human-readable board identifier (default: "default").

    Examples
    --------
    >>> board = KanbanBoard("sprint-1")
    >>> task = Task(id="t1", title="Fix bug", agent="codex")
    >>> board.add_task(task)
    >>> board.move_task("t1", "in_progress")
    >>> board.column_size("in_progress")
    1
    >>> board.get_board_state()["in_progress"][0]["title"]
    'Fix bug'
    """

    VALID_COLUMNS = ["todo", "in_progress", "review", "done"]

    def __init__(self, name: str = "default") -> None:
        self.name: str = name
        self._columns: Dict[str, Dict[str, Task]] = {col: {} for col in self.VALID_COLUMNS}

    # ------------------------------------------------------------------
    # Task operations
    # ------------------------------------------------------------------

    def add_task(self, task: Task, column: str = "todo") -> None:
        """Add a task to the board (default column: todo).

        Parameters
        ----------
        task : Task
            The task to add.
        column : str
            Target column name (must be one of VALID_COLUMNS).

        Raises
        ------
        ValueError
            If a task with the same id already exists, or if ``column`` is invalid.
        """
        self._validate_column(column)
        if task.id in self._all_tasks():
            raise ValueError(f"Task with id '{task.id}' already exists on the board.")
        self._columns[column][task.id] = task

    def move_task(self, task_id: str, target_column: str) -> Task:
        """Move an existing task to a different column.

        Parameters
        ----------
        task_id : str
            Identifier of the task to move.
        target_column : str
            Name of the destination column.

        Returns
        -------
        Task
            The moved task (now referenced by the target column).

        Raises
        ------
        KeyError
            If the task is not found on any column.
        ValueError
            If ``target_column`` is invalid.
        """
        self._validate_column(target_column)
        task = self._find_task(task_id)
        for col in self.VALID_COLUMNS:
            if task_id in self._columns[col]:
                del self._columns[col][task_id]
                break
        self._columns[target_column][task_id] = task
        return task

    def remove_task(self, task_id: str) -> Task:
        """Remove a task entirely from the board.

        Parameters
        ----------
        task_id : str
            Identifier of the task to remove.

        Returns
        -------
        Task
            The removed task instance.

        Raises
        ------
        KeyError
            If the task is not found.
        """
        task = self._find_task(task_id)
        for col in self.VALID_COLUMNS:
            if task_id in self._columns[col]:
                del self._columns[col][task_id]
                break
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Look up a task by id.

        Parameters
        ----------
        task_id : str
            Identifier of the task to find.

        Returns
        -------
        Task or None
            The task if found, otherwise ``None``.
        """
        try:
            return self._find_task(task_id)
        except KeyError:
            return None

    # ------------------------------------------------------------------
    # Board state
    # ------------------------------------------------------------------

    def get_board_state(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return the full board state as column -> list-of-dicts.

        Returns
        -------
        dict of str -> list of dict
            Keys are column names; values are lists of serialized task dicts.
        """
        state: Dict[str, List[Dict[str, Any]]] = {}
        for col in self.VALID_COLUMNS:
            state[col] = [t.to_dict() for t in self._columns[col].values()]
        return state

    def column_size(self, column: str) -> int:
        """Return number of items in a column.

        Parameters
        ----------
        column : str
            Column name to query.

        Returns
        -------
        int
            Number of tasks currently in that column.
        """
        self._validate_column(column)
        return len(self._columns[column])

    def tasks_by_agent(self, agent: str) -> List[Task]:
        """Return all tasks assigned to a particular agent.

        Parameters
        ----------
        agent : str
            Agent type string to filter by.

        Returns
        -------
        list of Task
            All tasks whose ``agent`` field matches.
        """
        result: List[Task] = []
        for task in self._all_tasks().values():
            if task.agent == agent:
                result.append(task)
        return result

    def get_tasks_sorted_by_priority(self, reverse: bool = True) -> List[Task]:
        """Return all tasks sorted by priority (highest first by default).

        Parameters
        ----------
        reverse : bool
            If True (default), highest priority first.
            If False, lowest priority first.

        Returns
        -------
        list of Task
            All tasks sorted by priority value.
        """
        tasks = list(self._all_tasks().values())
        tasks.sort(key=lambda t: t.priority.value, reverse=reverse)
        return tasks

    def clear(self) -> None:
        """Remove all tasks from every column, resetting the board."""
        for col in self.VALID_COLUMNS:
            self._columns[col].clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_column(self, column: str) -> None:
        if column not in self.VALID_COLUMNS:
            raise ValueError(
                f"Invalid column '{column}'. Valid columns: {', '.join(self.VALID_COLUMNS)}"
            )

    def _find_task(self, task_id: str) -> Task:
        for col in self.VALID_COLUMNS:
            if task_id in self._columns[col]:
                return self._columns[col][task_id]
        raise KeyError(f"Task '{task_id}' not found on board '{self.name}'.")

    def _all_tasks(self) -> Dict[str, Task]:
        all_: Dict[str, Task] = {}
        for col in self.VALID_COLUMNS:
            all_.update(self._columns[col])
        return all_

    def __repr__(self) -> str:
        sizes = {col: len(self._columns[col]) for col in self.VALID_COLUMNS}
        return f"KanbanBoard(name={self.name!r}, columns={sizes})"
