"""
agentix — Three agents. One board. Nobody waiting on a human.

A Python framework for multi-agent workflow orchestration using Kanban boards.
"""

from agentix.core import OrchestratorEngine
from agentix.pipeline import Pipeline
from agentix.kanban import KanbanBoard, Task, TaskStatus
from agentix.priority import Priority
from agentix.agents.base import BaseAgent
from agentix.agents.codex_agent import CodexAgent
from agentix.agents.review_agent import ReviewAgent
from agentix.exceptions import (
    AgentixError,
    PipelineError,
    PipelineNotFoundError,
    StageNotFoundError,
    CycleDetectedError,
    BoardError,
    TaskNotFoundError,
    ValidationError,
    TimeoutError,
    RetryExhaustedError,
)
from agentix.config import PipelineConfig, StageConfig
from agentix.scheduler import PipelineScheduler
from agentix.controller import PipelineController
from agentix.board import BoardManager
from agentix.metrics import StageMetrics, StageTiming
from agentix.report import generate_pipeline_report, generate_board_report
from agentix.templates import list_presets, get_preset, get_preset_description
from agentix.themes import get_theme, list_themes, ColorTheme

__all__ = [
    "OrchestratorEngine",
    "Pipeline",
    "KanbanBoard",
    "Task",
    "TaskStatus",
    "Priority",
    "BaseAgent",
    "CodexAgent",
    "ReviewAgent",
    "AgentixError",
    "PipelineError",
    "PipelineNotFoundError",
    "StageNotFoundError",
    "CycleDetectedError",
    "BoardError",
    "TaskNotFoundError",
    "ValidationError",
    "TimeoutError",
    "RetryExhaustedError",
    "PipelineConfig",
    "StageConfig",
    "PipelineScheduler",
    "PipelineController",
    "BoardManager",
    "StageMetrics",
    "StageTiming",
    "generate_pipeline_report",
    "generate_board_report",
    "list_presets",
    "get_preset",
    "get_preset_description",
    "get_theme",
    "list_themes",
    "ColorTheme",
]

__version__ = "0.1.0"
