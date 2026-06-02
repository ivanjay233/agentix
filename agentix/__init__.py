"""
agentix — Three agents. One board. Nobody waiting on a human.

A Python framework for multi-agent workflow orchestration using Kanban boards.
"""

from agentix.core import OrchestratorEngine
from agentix.pipeline import Pipeline
from agentix.kanban import KanbanBoard, Task, TaskStatus
from agentix.agents.base import BaseAgent
from agentix.agents.codex_agent import CodexAgent
from agentix.agents.review_agent import ReviewAgent

__all__ = [
    "OrchestratorEngine",
    "Pipeline",
    "KanbanBoard",
    "Task",
    "TaskStatus",
    "BaseAgent",
    "CodexAgent",
    "ReviewAgent",
]

__version__ = "0.1.0"
