"""Priority levels for Kanban tasks."""
from enum import IntEnum, auto


class Priority(IntEnum):
    """Task priority levels — higher value = higher urgency."""

    LOWEST = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()
