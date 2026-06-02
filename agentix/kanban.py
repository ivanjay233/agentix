"""
KanbanBoard — columns: todo, in_progress, review, done.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
    """Possible states for a task on the Kanban board."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


class Task:
    """A single unit of work tracked on the Kanban board."""

    def __init__(
        self,
        id: Optional[str] = None,
        title: str = "",
        stage: str = "",
        agent: str = "",
        status: TaskStatus = TaskStatus.TODO,
        artifacts: Any = None,
    ) -> None:
        self.id: str = id or uuid.uuid4().hex[:12]
        self.title: str = title
        self.stage: str = stage
        self.agent: str = agent
        self.status: TaskStatus = status
        self.artifacts: Any = artifacts
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def update_status(self, new_status: TaskStatus) -> None:
        """Transition this task to a new status."""
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict (for display / export)."""
        return {
            "id": self.id,
            "title": self.title,
            "stage": self.stage,
            "agent": self.agent,
            "status": self.status.value,
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
    """

    VALID_COLUMNS = ["todo", "in_progress", "review", "done"]

    def __init__(self, name: str = "default") -> None:
        self.name: str = name
        self._columns: Dict[str, Dict[str, Task]] = {col: {} for col in self.VALID_COLUMNS}

    # ------------------------------------------------------------------
    # Task operations
    # ------------------------------------------------------------------

    def add_task(self, task: Task, column: str = "todo") -> None:
        """Add a task to the board (default column: todo)."""
        self._validate_column(column)
        if task.id in self._all_tasks():
            raise ValueError(f"Task with id '{task.id}' already exists on the board.")
        self._columns[column][task.id] = task

    def move_task(self, task_id: str, target_column: str) -> Task:
        """Move an existing task to a different column."""
        self._validate_column(target_column)
        task = self._find_task(task_id)
        # Remove from current column
        for col in self.VALID_COLUMNS:
            if task_id in self._columns[col]:
                del self._columns[col][task_id]
                break
        # Place in target column
        self._columns[target_column][task_id] = task
        return task

    def remove_task(self, task_id: str) -> Task:
        """Remove a task entirely from the board."""
        task = self._find_task(task_id)
        for col in self.VALID_COLUMNS:
            if task_id in self._columns[col]:
                del self._columns[col][task_id]
                break
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Look up a task by id, or None."""
        try:
            return self._find_task(task_id)
        except KeyError:
            return None

    # ------------------------------------------------------------------
    # Board state
    # ------------------------------------------------------------------

    def get_board_state(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return the full board state as column -> list-of-dicts."""
        state: Dict[str, List[Dict[str, Any]]] = {}
        for col in self.VALID_COLUMNS:
            state[col] = [t.to_dict() for t in self._columns[col].values()]
        return state

    def column_size(self, column: str) -> int:
        """Return number of items in a column."""
        self._validate_column(column)
        return len(self._columns[column])

    def tasks_by_agent(self, agent: str) -> List[Task]:
        """Return all tasks assigned to a particular agent."""
        result: List[Task] = []
        for task in self._all_tasks().values():
            if task.agent == agent:
                result.append(task)
        return result

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
