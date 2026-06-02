"""Agentix exception hierarchy — all custom exceptions in one module."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class AgentixError(Exception):
    """Base exception for all agentix errors."""


class PipelineError(AgentixError):
    """Errors related to pipeline definition or execution."""


class PipelineNotFoundError(PipelineError):
    """Raised when a requested pipeline does not exist."""

    def __init__(self, name: str) -> None:
        self.pipeline_name = name
        super().__init__(f"Pipeline '{name}' not found.")


class PipelineExistsError(PipelineError):
    """Raised when creating a pipeline with a duplicate name."""

    def __init__(self, name: str) -> None:
        self.pipeline_name = name
        super().__init__(f"Pipeline '{name}' already exists.")


class StageNotFoundError(PipelineError):
    """Raised when a requested stage does not exist in a pipeline."""

    def __init__(self, stage_name: str, pipeline_name: str) -> None:
        self.stage_name = stage_name
        self.pipeline_name = pipeline_name
        super().__init__(f"Stage '{stage_name}' not found in pipeline '{pipeline_name}'.")


class StageExistsError(PipelineError):
    """Raised when adding a stage with a duplicate name."""

    def __init__(self, stage_name: str, pipeline_name: str) -> None:
        self.stage_name = stage_name
        self.pipeline_name = pipeline_name
        super().__init__(f"Stage '{stage_name}' already exists in pipeline '{pipeline_name}'.")


class CycleDetectedError(PipelineError):
    """Raised when a pipeline's dependency graph contains a cycle."""

    def __init__(self, pipeline_name: str) -> None:
        self.pipeline_name = pipeline_name
        super().__init__(f"Cycle detected in pipeline '{pipeline_name}'.")


class DeadlockError(PipelineError):
    """Raised when concurrent execution reaches a deadlock."""

    def __init__(self, pending: int, completed: int) -> None:
        self.pending = pending
        self.completed = completed
        super().__init__(
            f"Deadlock detected — {pending} stages pending but none ready. "
            f"Completed: {completed}"
        )


class BoardError(AgentixError):
    """Errors related to Kanban board operations."""


class InvalidColumnError(BoardError):
    """Raised when an invalid column name is used."""

    def __init__(self, column: str, valid_columns: List[str]) -> None:
        self.column = column
        self.valid_columns = valid_columns
        super().__init__(
            f"Invalid column '{column}'. Valid columns: {', '.join(valid_columns)}"
        )


class TaskNotFoundError(BoardError):
    """Raised when a task is not found on the board."""

    def __init__(self, task_id: str, board_name: str) -> None:
        self.task_id = task_id
        self.board_name = board_name
        super().__init__(f"Task '{task_id}' not found on board '{board_name}'.")


class TaskExistsError(BoardError):
    """Raised when adding a task with a duplicate id."""

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"Task with id '{task_id}' already exists on the board.")


class AgentError(AgentixError):
    """Errors related to agents."""


class AgentNotFoundError(AgentError):
    """Raised when a requested agent is not registered."""

    def __init__(self, name: str, available: Optional[List[str]] = None) -> None:
        self.agent_name = name
        msg = f"Agent '{name}' not found in registry."
        if available:
            msg += f" Available: {', '.join(sorted(available))}"
        super().__init__(msg)


class ValidationError(AgentixError):
    """Pipeline configuration validation errors."""

    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        super().__init__(f"Pipeline validation failed with {len(errors)} error(s): {'; '.join(errors)}")


class TimeoutError(AgentixError):
    """Raised when a stage exceeds its timeout."""

    def __init__(self, stage_name: str, timeout: float) -> None:
        self.stage_name = stage_name
        self.timeout = timeout
        super().__init__(f"Stage '{stage_name}' timed out after {timeout:.1f}s.")


class RetryExhaustedError(AgentixError):
    """Raised when all retry attempts for a stage have been exhausted."""

    def __init__(self, stage_name: str, retries: int, last_error: str) -> None:
        self.stage_name = stage_name
        self.retries = retries
        self.last_error = last_error
        super().__init__(
            f"Stage '{stage_name}' failed after {retries} retries: {last_error}"
        )


class InvalidStatusTransitionError(BoardError):
    """Raised when a task status transition is not allowed."""

    def __init__(self, task_id: str, from_status: str, to_status: str) -> None:
        self.task_id = task_id
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Invalid status transition for task '{task_id}': "
            f"'{from_status}' -> '{to_status}'"
        )
