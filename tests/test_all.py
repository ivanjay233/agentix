"""Comprehensive test suite for agentix — pipeline, board, tasks, scheduler, and CLI."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agentix.core import OrchestratorEngine
from agentix.pipeline import Pipeline
from agentix.kanban import KanbanBoard, Task, TaskStatus, is_valid_transition
from agentix.priority import Priority
from agentix.scheduler import PipelineScheduler
from agentix.dryrun import dry_run, DryRunResult
from agentix.validation import validate_pipeline_config
from agentix.config import PipelineConfig, StageConfig
from agentix.controller import PipelineController
from agentix.board import BoardManager
from agentix.metrics import StageMetrics, StageTiming
from agentix.report import generate_pipeline_report, generate_board_report
from agentix.templates import list_presets, get_preset, get_preset_description
from agentix.exceptions import (
    CycleDetectedError,
    InvalidColumnError,
    StageNotFoundError,
    TaskNotFoundError,
    ValidationError,
)
from agentix.agents.base import BaseAgent
from agentix.agents.codex_agent import CodexAgent
from agentix.agents.review_agent import ReviewAgent


# ===================================================================
# Pipeline Tests
# ===================================================================


class TestPipeline:
    def test_create_pipeline(self) -> None:
        p = Pipeline(name="test")
        assert p.name == "test"
        assert p.stages == []

    def test_add_stage(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("write", "codex", input_keys=["topic"], output_keys=["draft"])
        assert len(p.stages) == 1
        assert p.stages[0]["name"] == "write"
        assert p.stages[0]["agent_type"] == "codex"
        assert p.stages[0]["input_keys"] == ["topic"]
        assert p.stages[0]["output_keys"] == ["draft"]
        assert p.stages[0]["depends_on"] == []

    def test_add_duplicate_stage_raises(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("write", "codex")
        with pytest.raises(ValueError, match="already exists"):
            p.add_stage("write", "codex")

    def test_remove_stage(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("write", "codex")
        p.add_stage("review", "reviewer")
        p.remove_stage("write")
        assert len(p.stages) == 1
        assert p.stages[0]["name"] == "review"

    def test_remove_missing_stage_raises(self) -> None:
        p = Pipeline(name="test")
        with pytest.raises(KeyError):
            p.remove_stage("nonexistent")

    def test_get_stage(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("write", "codex")
        s = p.get_stage("write")
        assert s["agent_type"] == "codex"

    def test_get_stage_missing_raises(self) -> None:
        p = Pipeline(name="test")
        with pytest.raises(KeyError):
            p.get_stage("nonexistent")

    def test_empty_pipeline(self) -> None:
        p = Pipeline(name="empty")
        assert p.topological_sort() == []

    def test_single_stage(self) -> None:
        p = Pipeline(name="single")
        p.add_stage("only", "agent")
        assert p.topological_sort() == ["only"]

    def test_topological_sort_linear(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", depends_on=[])
        p.add_stage("b", "agent", depends_on=["a"])
        p.add_stage("c", "agent", depends_on=["b"])
        assert p.topological_sort() == ["a", "b", "c"]

    def test_topological_sort_diamond(self) -> None:
        p = Pipeline(name="diamond")
        p.add_stage("a", "agent", depends_on=[])
        p.add_stage("b", "agent", depends_on=["a"])
        p.add_stage("c", "agent", depends_on=["a"])
        p.add_stage("d", "agent", depends_on=["b", "c"])
        order = p.topological_sort()
        assert order[0] == "a"
        assert order[-1] == "d"

    def test_topological_sort_parallel(self) -> None:
        p = Pipeline(name="parallel")
        p.add_stage("a", "agent", depends_on=[])
        p.add_stage("b", "agent", depends_on=[])
        p.add_stage("c", "agent", depends_on=[])
        order = p.topological_sort()
        assert set(order) == {"a", "b", "c"}

    def test_topological_sort_cycle_raises(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", depends_on=["c"])
        p.add_stage("b", "agent", depends_on=["a"])
        p.add_stage("c", "agent", depends_on=["b"])
        with pytest.raises(RuntimeError, match="Cycle"):
            p.topological_sort()

    def test_dependency_graph(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", depends_on=[])
        p.add_stage("b", "agent", depends_on=["a"])
        graph = p.dependency_graph()
        assert graph == {"a": [], "b": ["a"]}

    def test_repr(self) -> None:
        p = Pipeline(name="test", stages=[{"name": "s1", "agent_type": "a"}])
        assert repr(p) == "Pipeline(name='test', stages=1)"


# ===================================================================
# YAML Serialization Tests
# ===================================================================


class TestPipelineYAML:
    def test_yaml_roundtrip(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("write", "codex", input_keys=["topic"], output_keys=["draft"])
        p.add_stage("review", "review_agent", depends_on=["write"])
        yaml_str = p.to_yaml()
        p2 = Pipeline.from_yaml(yaml_str)
        assert p2.name == p.name
        assert len(p2.stages) == len(p.stages)
        assert p2.stages[0]["name"] == "write"

    def test_json_roundtrip(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("write", "codex")
        json_str = p.to_json()
        p2 = Pipeline.from_json(json_str)
        assert p2.name == "test"
        assert len(p2.stages) == 1

    def test_from_yaml_file(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("write", "codex")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(p.to_yaml())
            f.flush()
            p2 = Pipeline.from_yaml_file(f.name)
            assert p2.name == "test"
        os.unlink(f.name)

    def test_yaml_invalid_root(self) -> None:
        with pytest.raises(ValueError, match="YAML"):
            Pipeline.from_yaml("not a mapping")

    def test_yaml_empty_stages(self) -> None:
        p = Pipeline.from_yaml("name: empty\nstages: []")
        assert p.name == "empty"
        assert p.stages == []

    def test_yaml_no_name(self) -> None:
        p = Pipeline.from_yaml("stages: []")
        assert p.name == "unnamed"


# ===================================================================
# Task Tests
# ===================================================================


class TestTask:
    def test_default_status(self) -> None:
        t = Task()
        assert t.status == TaskStatus.TODO

    def test_default_priority(self) -> None:
        t = Task()
        assert t.priority == Priority.MEDIUM

    def test_update_status(self) -> None:
        t = Task()
        t.update_status(TaskStatus.IN_PROGRESS)
        assert t.status == TaskStatus.IN_PROGRESS

    def test_invalid_status_transition(self) -> None:
        t = Task()
        with pytest.raises(ValueError, match="Invalid status transition"):
            t.update_status(TaskStatus.DONE)  # TODO -> DONE is invalid

    def test_valid_transition_review_to_in_progress(self) -> None:
        t = Task(status=TaskStatus.REVIEW)
        t.update_status(TaskStatus.IN_PROGRESS)
        assert t.status == TaskStatus.IN_PROGRESS

    def test_valid_transition_in_progress_to_done(self) -> None:
        t = Task(status=TaskStatus.IN_PROGRESS)
        t.update_status(TaskStatus.DONE)
        assert t.status == TaskStatus.DONE

    def test_is_valid_transition(self) -> None:
        assert is_valid_transition("todo", "in_progress")
        assert not is_valid_transition("todo", "done")
        assert is_valid_transition("in_progress", "review")
        assert is_valid_transition("in_progress", "done")
        assert not is_valid_transition("done", "todo")

    def test_assign(self) -> None:
        t = Task()
        t.assign("alice")
        assert t.assignee == "alice"

    def test_to_dict(self) -> None:
        t = Task(id="abc", title="Test", stage="write", agent="codex", assignee="bob")
        d = t.to_dict()
        assert d["id"] == "abc"
        assert d["title"] == "Test"
        assert d["stage"] == "write"
        assert d["agent"] == "codex"
        assert d["assignee"] == "bob"
        assert d["status"] == "todo"

    def test_to_dict_with_priority(self) -> None:
        t = Task(id="t1", title="Critical", priority=Priority.CRITICAL)
        d = t.to_dict()
        assert d["priority"] == "CRITICAL"

    def test_auto_id(self) -> None:
        t = Task(title="auto-id")
        assert len(t.id) == 12

    def test_repr(self) -> None:
        t = Task(id="t1", title="test")
        assert "Task(id='t1'" in repr(t)
        assert "title='test'" in repr(t)


# ===================================================================
# KanbanBoard Tests
# ===================================================================


class TestKanbanBoard:
    def test_add_task(self) -> None:
        board = KanbanBoard(name="test")
        task = Task(id="t1", title="Write docs", stage="write", agent="codex")
        board.add_task(task)
        assert board.column_size("todo") == 1

    def test_add_task_to_custom_column(self) -> None:
        board = KanbanBoard(name="test")
        task = Task(id="t1", title="In progress")
        board.add_task(task, column="in_progress")
        assert board.column_size("in_progress") == 1
        assert board.column_size("todo") == 0

    def test_duplicate_task_raises(self) -> None:
        board = KanbanBoard(name="test")
        board.add_task(Task(id="t1"))
        with pytest.raises(ValueError, match="already exists"):
            board.add_task(Task(id="t1"))

    def test_move_task(self) -> None:
        board = KanbanBoard(name="test")
        task = Task(id="t1", title="Write code")
        board.add_task(task)
        board.move_task("t1", "in_progress")
        assert board.column_size("todo") == 0
        assert board.column_size("in_progress") == 1
        t = board.get_task("t1")
        assert t is not None

    def test_move_nonexistent_task_raises(self) -> None:
        board = KanbanBoard(name="test")
        with pytest.raises(KeyError):
            board.move_task("nonexistent", "done")

    def test_remove_task(self) -> None:
        board = KanbanBoard(name="test")
        board.add_task(Task(id="t1"))
        removed = board.remove_task("t1")
        assert removed.id == "t1"
        assert board.get_task("t1") is None

    def test_remove_nonexistent_raises(self) -> None:
        board = KanbanBoard(name="test")
        with pytest.raises(KeyError):
            board.remove_task("nonexistent")

    def test_get_task_nonexistent_returns_none(self) -> None:
        board = KanbanBoard(name="test")
        assert board.get_task("nonexistent") is None

    def test_get_board_state(self) -> None:
        board = KanbanBoard(name="test")
        board.add_task(Task(id="t1", title="A"))
        board.add_task(Task(id="t2", title="B"))
        state = board.get_board_state()
        assert "todo" in state
        assert len(state["todo"]) == 2
        assert state["in_progress"] == []
        assert state["review"] == []
        assert state["done"] == []

    def test_clear_board(self) -> None:
        board = KanbanBoard(name="test")
        board.add_task(Task(id="t1"))
        board.add_task(Task(id="t2"))
        board.clear()
        assert board.column_size("todo") == 0
        assert sum(board.column_size(c) for c in board.VALID_COLUMNS) == 0

    def test_tasks_by_agent(self) -> None:
        board = KanbanBoard(name="test")
        board.add_task(Task(id="t1", agent="codex"))
        board.add_task(Task(id="t2", agent="review"))
        board.add_task(Task(id="t3", agent="codex"))
        assert len(board.tasks_by_agent("codex")) == 2
        assert len(board.tasks_by_agent("review")) == 1
        assert len(board.tasks_by_agent("nonexistent")) == 0

    def test_tasks_by_assignee(self) -> None:
        board = KanbanBoard(name="test")
        board.add_task(Task(id="t1", assignee="alice"))
        board.add_task(Task(id="t2", assignee="bob"))
        board.add_task(Task(id="t3", assignee="alice"))
        assert len(board.tasks_by_assignee("alice")) == 2
        assert len(board.tasks_by_assignee("bob")) == 1
        assert len(board.tasks_by_assignee("charlie")) == 0

    def test_get_tasks_sorted_by_priority(self) -> None:
        board = KanbanBoard(name="test")
        board.add_task(Task(id="t1", priority=Priority.LOW))
        board.add_task(Task(id="t2", priority=Priority.CRITICAL))
        board.add_task(Task(id="t3", priority=Priority.HIGH))
        sorted_tasks = board.get_tasks_sorted_by_priority()
        assert sorted_tasks[0].priority == Priority.CRITICAL
        assert sorted_tasks[-1].priority == Priority.LOW

    def test_invalid_column_raises(self) -> None:
        board = KanbanBoard(name="test")
        with pytest.raises(ValueError, match="Invalid column"):
            board.add_task(Task(id="t1"), column="invalid")

    def test_invalid_move_column_raises(self) -> None:
        board = KanbanBoard(name="test")
        board.add_task(Task(id="t1"))
        with pytest.raises(ValueError, match="Invalid column"):
            board.move_task("t1", "nope")

    def test_repr(self) -> None:
        board = KanbanBoard(name="test")
        board.add_task(Task(id="t1"))
        r = repr(board)
        assert "KanbanBoard(name='test'" in r

    def test_empty_board_state(self) -> None:
        board = KanbanBoard(name="empty")
        state = board.get_board_state()
        assert state == {"todo": [], "in_progress": [], "review": [], "done": []}


# ===================================================================
# OrchestratorEngine Tests
# ===================================================================


class TestOrchestratorEngine:
    def test_create_pipeline(self) -> None:
        engine = OrchestratorEngine()
        p = engine.create_pipeline("test")
        assert p.name == "test"
        assert "test" in engine.list_pipelines()

    def test_create_pipeline_with_stages(self) -> None:
        engine = OrchestratorEngine()
        stages = [{"name": "s1", "agent_type": "codex"}]
        p = engine.create_pipeline("test", stages=stages)
        assert len(p.stages) == 1

    def test_duplicate_pipeline_raises(self) -> None:
        engine = OrchestratorEngine()
        engine.create_pipeline("dup")
        with pytest.raises(ValueError, match="already exists"):
            engine.create_pipeline("dup")

    def test_get_pipeline(self) -> None:
        engine = OrchestratorEngine()
        engine.create_pipeline("my_pipe")
        p = engine.get_pipeline("my_pipe")
        assert p.name == "my_pipe"

    def test_get_missing_pipeline_raises(self) -> None:
        engine = OrchestratorEngine()
        with pytest.raises(KeyError):
            engine.get_pipeline("nope")

    def test_list_pipelines(self) -> None:
        engine = OrchestratorEngine()
        engine.create_pipeline("b")
        engine.create_pipeline("a")
        assert engine.list_pipelines() == ["a", "b"]

    def test_get_board(self) -> None:
        engine = OrchestratorEngine()
        engine.create_pipeline("test")
        board = engine.get_board("test")
        assert board.name == "test_board"

    def test_get_board_missing_raises(self) -> None:
        engine = OrchestratorEngine()
        with pytest.raises(KeyError):
            engine.get_board("nope")

    def test_empty_pipeline_execution(self) -> None:
        engine = OrchestratorEngine()
        engine.create_pipeline("empty")
        result = asyncio.run(engine.run("empty", inputs={"key": "val"}))
        assert result == {"key": "val"}

    @pytest.mark.asyncio
    async def test_run_pipeline(self) -> None:
        engine = OrchestratorEngine()
        engine.create_pipeline(
            "simple",
            stages=[
                {
                    "name": "stage1",
                    "agent_type": "test_agent",
                    "input_keys": ["input"],
                    "output_keys": ["output"],
                    "depends_on": [],
                }
            ],
        )
        result = await engine.run("simple", inputs={"input": "hello"})
        assert "output" in result

    @pytest.mark.asyncio
    async def test_pause_resume(self) -> None:
        engine = OrchestratorEngine()
        engine.create_pipeline("pausable")
        assert not engine.is_paused()
        engine.pause()
        assert engine.is_paused()
        engine.resume()
        assert not engine.is_paused()

    def test_shutdown(self) -> None:
        engine = OrchestratorEngine()
        engine.create_pipeline("test")
        engine.shutdown()
        assert not engine.is_running()


# ===================================================================
# PipelineScheduler Tests
# ===================================================================


class TestPipelineScheduler:
    def test_ordered_stages(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", depends_on=[])
        p.add_stage("b", "agent", depends_on=["a"])
        scheduler = PipelineScheduler(p)
        assert scheduler.ordered_stages() == ["a", "b"]

    def test_ready_stages(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", depends_on=[])
        p.add_stage("b", "agent", depends_on=["a"])
        p.add_stage("c", "agent", depends_on=["a", "b"])
        scheduler = PipelineScheduler(p)
        assert scheduler.ready_stages(set()) == ["a"]
        assert scheduler.ready_stages({"a"}) == ["b"]
        assert scheduler.ready_stages({"a", "b"}) == ["c"]

    def test_pending_stages(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent")
        p.add_stage("b", "agent")
        scheduler = PipelineScheduler(p)
        assert set(scheduler.pending_stages(set())) == {"a", "b"}
        assert scheduler.pending_stages({"a"}) == ["b"]

    def test_has_cycle(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", depends_on=["b"])
        p.add_stage("b", "agent", depends_on=["a"])
        scheduler = PipelineScheduler(p)
        assert scheduler.has_cycle()

    def test_no_cycle(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent")
        p.add_stage("b", "agent", depends_on=["a"])
        scheduler = PipelineScheduler(p)
        assert not scheduler.has_cycle()

    def test_critical_path(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", depends_on=[])
        p.add_stage("b", "agent", depends_on=["a"])
        p.add_stage("c", "agent", depends_on=["b"])
        scheduler = PipelineScheduler(p)
        assert scheduler.critical_path() == 3

    def test_critical_path_parallel(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", depends_on=[])
        p.add_stage("b", "agent", depends_on=[])
        scheduler = PipelineScheduler(p)
        assert scheduler.critical_path() == 1

    def test_levels(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", depends_on=[])
        p.add_stage("b", "agent", depends_on=[])
        p.add_stage("c", "agent", depends_on=["a", "b"])
        scheduler = PipelineScheduler(p)
        levels = scheduler.levels()
        assert len(levels) == 2
        assert set(levels[0]) == {"a", "b"}
        assert levels[1] == ["c"]

    def test_empty_pipeline(self) -> None:
        p = Pipeline(name="empty")
        scheduler = PipelineScheduler(p)
        assert scheduler.ordered_stages() == []
        assert scheduler.levels() == []


# ===================================================================
# Dry-run Tests
# ===================================================================


class TestDryRun:
    def test_valid_pipeline(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", output_keys=["x"])
        p.add_stage("b", "agent", input_keys=["x"], depends_on=["a"])
        result = dry_run(p)
        assert result.valid
        assert len(result.stage_order) == 2

    def test_invalid_missing_input_key(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", input_keys=["missing"])
        result = dry_run(p)
        assert not result.valid
        assert any("input_key" in e for e in result.errors)

    def test_cycle_detected(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", depends_on=["b"])
        p.add_stage("b", "agent", depends_on=["a"])
        result = dry_run(p)
        assert not result.valid

    def test_empty_pipeline_dry_run(self) -> None:
        p = Pipeline(name="empty")
        result = dry_run(p)
        assert not result.valid  # no stages

    def test_dry_run_dict(self) -> None:
        p = Pipeline(name="test")
        result = dry_run(p)
        d = result.to_dict()
        assert "valid" in d
        assert "stage_order" in d
        assert "errors" in d


# ===================================================================
# Validation Tests
# ===================================================================


class TestValidation:
    def test_valid_config(self) -> None:
        config = {"name": "test", "stages": [{"name": "s1", "agent_type": "codex"}]}
        errors = validate_pipeline_config(config)
        assert errors == []

    def test_missing_name(self) -> None:
        config = {"stages": []}
        errors = validate_pipeline_config(config)
        assert any("name" in e for e in errors)

    def test_stages_not_list(self) -> None:
        config = {"name": "test", "stages": "not_a_list"}
        errors = validate_pipeline_config(config)
        assert any("list" in e for e in errors)

    def test_empty_stages(self) -> None:
        config = {"name": "test", "stages": []}
        errors = validate_pipeline_config(config)
        assert any("at least one" in e for e in errors)

    def test_duplicate_stage_name(self) -> None:
        config = {"name": "test", "stages": [{"name": "s1", "agent_type": "a"}, {"name": "s1", "agent_type": "b"}]}
        errors = validate_pipeline_config(config)
        assert any("duplicate" in e for e in errors)

    def test_missing_dependency(self) -> None:
        config = {"name": "test", "stages": [{"name": "s1", "agent_type": "a", "depends_on": ["missing"]}]}
        errors = validate_pipeline_config(config)
        assert any("depends_on" in e for e in errors)

    def test_invalid_stage_type(self) -> None:
        config = {"name": "test", "stages": ["not a dict"]}
        errors = validate_pipeline_config(config)
        assert any("dictionary" in e for e in errors)


# ===================================================================
# Config Models Tests
# ===================================================================


class TestConfigModels:
    def test_stage_config_to_dict(self) -> None:
        sc = StageConfig(name="test", agent_type="codex", input_keys=["a"], output_keys=["b"])
        d = sc.to_dict()
        assert d["name"] == "test"
        assert d["input_keys"] == ["a"]

    def test_stage_config_from_dict(self) -> None:
        sc = StageConfig.from_dict({"name": "test", "agent_type": "codex"})
        assert sc.name == "test"
        assert sc.agent_type == "codex"

    def test_pipeline_config_roundtrip(self) -> None:
        pc = PipelineConfig(name="test", stages=[StageConfig(name="s1", agent_type="codex")])
        d = pc.to_dict()
        pc2 = PipelineConfig.from_dict(d)
        assert pc2.name == "test"
        assert len(pc2.stages) == 1
        assert pc2.stages[0].name == "s1"


# ===================================================================
# Controller Tests
# ===================================================================


class TestPipelineController:
    @pytest.mark.asyncio
    async def test_run(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("s1", "agent", output_keys=["out"])
        board = KanbanBoard("test_board")
        ctrl = PipelineController(p, board)
        result = await ctrl.run({"in": 1})
        assert "out" in result or result == {"in": 1}

    def test_pause_resume(self) -> None:
        p = Pipeline(name="test")
        board = KanbanBoard("test_board")
        ctrl = PipelineController(p, board)
        assert not ctrl.is_paused
        ctrl.pause()
        assert ctrl.is_paused
        ctrl.resume()
        assert not ctrl.is_paused


# ===================================================================
# BoardManager Tests
# ===================================================================


class TestBoardManager:
    def test_create_task(self) -> None:
        board = KanbanBoard("test")
        mgr = BoardManager(board)
        task = mgr.create_task("t1", "Write tests", "test", "codex")
        assert task.title == "Write tests"
        assert board.column_size("todo") == 1

    def test_start_task(self) -> None:
        board = KanbanBoard("test")
        mgr = BoardManager(board)
        mgr.create_task("t1", "Task 1")
        mgr.start_task("t1")
        assert board.column_size("in_progress") == 1

    def test_complete_task(self) -> None:
        board = KanbanBoard("test")
        mgr = BoardManager(board)
        mgr.create_task("t1", "Task 1")
        mgr.start_task("t1")
        mgr.complete_task("t1", {"result": "ok"})
        assert board.column_size("done") == 1

    def test_task_count(self) -> None:
        board = KanbanBoard("test")
        mgr = BoardManager(board)
        mgr.create_task("t1", "Task 1")
        mgr.create_task("t2", "Task 2")
        assert mgr.task_count() == 2

    def test_summary(self) -> None:
        board = KanbanBoard("test")
        mgr = BoardManager(board)
        mgr.create_task("t1", "Task 1")
        s = mgr.summary()
        assert s["todo"] == 1

    def test_get_stats(self) -> None:
        board = KanbanBoard("test")
        mgr = BoardManager(board)
        mgr.create_task("t1", "Task 1", agent="codex")
        stats = mgr.get_stats()
        assert stats["total_tasks"] == 1
        assert stats["by_agent"]["codex"] == 1


# ===================================================================
# StageMetrics Tests
# ===================================================================


class TestStageMetrics:
    def test_start_and_finish(self) -> None:
        metrics = StageMetrics()
        timing = metrics.start_stage("extract", "reader")
        import time
        time.sleep(0.01)
        metrics.finish_stage(timing)
        assert timing.duration is not None
        assert timing.duration > 0

    def test_total_time(self) -> None:
        metrics = StageMetrics()
        t1 = metrics.start_stage("a")
        metrics.finish_stage(t1)
        t2 = metrics.start_stage("b")
        metrics.finish_stage(t2)
        assert metrics.total_time() > 0

    def test_count_by_status(self) -> None:
        metrics = StageMetrics()
        t1 = metrics.start_stage("a")
        metrics.finish_stage(t1)
        counts = metrics.count_by_status()
        assert counts.get("completed", 0) >= 1

    def test_clear(self) -> None:
        metrics = StageMetrics()
        t1 = metrics.start_stage("a")
        metrics.finish_stage(t1)
        metrics.clear()
        assert metrics.total_time() == 0.0

    def test_report(self) -> None:
        metrics = StageMetrics()
        t1 = metrics.start_stage("a")
        metrics.finish_stage(t1)
        report = metrics.report()
        assert "total_stages" in report
        assert "total_time" in report


# ===================================================================
# Report Tests
# ===================================================================


class TestReport:
    def test_generate_pipeline_report(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("s1", "codex", output_keys=["out"])
        report = generate_pipeline_report(p)
        assert "Pipeline Report: test" in report
        assert "s1" in report
        assert "codex" in report

    def test_generate_board_report(self) -> None:
        board = KanbanBoard("test")
        board.add_task(Task(id="t1", title="Task 1"))
        report = generate_board_report(board)
        assert "Kanban Board: test" in report
        assert "Task 1" in report


# ===================================================================
# Templates Tests
# ===================================================================


class TestTemplates:
    def test_list_presets(self) -> None:
        presets = list_presets()
        assert "code-review" in presets
        assert "data-pipeline" in presets
        assert "ci-cd" in presets

    def test_get_preset(self) -> None:
        preset = get_preset("code-review")
        assert preset is not None
        assert preset["name"] == "code-review"
        assert len(preset["stages"]) >= 2

    def test_get_nonexistent_preset(self) -> None:
        preset = get_preset("nonexistent")
        assert preset is None

    def test_get_preset_description(self) -> None:
        desc = get_preset_description("code-review")
        assert desc is not None
        assert "code review" in desc.lower()


# ===================================================================
# Agents Tests
# ===================================================================


class TestBaseAgent:
    def test_abstract_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            BaseAgent()

    def test_concrete_agent(self) -> None:
        class DummyAgent(BaseAgent):
            async def process(self, task):
                return {"result": "ok"}
            def validate(self):
                return True
            def report(self):
                return "dummy report"

        agent = DummyAgent(name="dummy")
        assert agent.name == "dummy"
        assert agent.validate() is True
        assert agent.report() == "dummy report"


class TestReviewAgent:
    @pytest.mark.asyncio
    async def test_process_good_code(self) -> None:
        agent = ReviewAgent()
        result = await agent.process({"content": "x = 1"})
        assert result["passed"] is True
        assert result["score"] >= 50

    @pytest.mark.asyncio
    async def test_process_bad_syntax(self) -> None:
        agent = ReviewAgent()
        result = await agent.process({"content": "def broken("})
        assert not result["passed"]
        assert any("Syntax error" in i for i in result["issues"])

    @pytest.mark.asyncio
    async def test_process_anti_patterns(self) -> None:
        agent = ReviewAgent()
        result = await agent.process({"content": 'eval("print(1)")'})
        assert any("eval" in i.lower() for i in result["issues"])

    def test_validate(self) -> None:
        agent = ReviewAgent()
        assert agent.validate() is True

    def test_report(self) -> None:
        agent = ReviewAgent()
        report = agent.report()
        assert "reviewed 0 task(s)" in report


class TestCodexAgent:
    @pytest.mark.asyncio
    async def test_process_mock_fallback(self) -> None:
        agent = CodexAgent()
        result = await agent.process({"prompt": "write hello", "language": "python"})
        assert "code" in result
        assert result["language"] == "python"

    @pytest.mark.asyncio
    async def test_process_requires_prompt(self) -> None:
        agent = CodexAgent()
        with pytest.raises(ValueError, match="prompt"):
            await agent.process({"language": "python"})

    def test_validate(self) -> None:
        agent = CodexAgent()
        assert agent.validate() is False

    def test_report(self) -> None:
        agent = CodexAgent()
        r = agent.report()
        assert "processed 0 task(s)" in r


# ===================================================================
# Stress Test
# ===================================================================


class TestStress:
    @pytest.mark.asyncio
    async def test_1000_tasks_on_board(self) -> None:
        board = KanbanBoard(name="stress")
        for i in range(1000):
            board.add_task(Task(id=f"t{i:04d}", title=f"Task {i}", stage="stress", agent="codex"))
        assert board.column_size("todo") == 1000
        assert board.column_size("in_progress") == 0
        assert board.column_size("done") == 0

        # Move half to in_progress
        for i in range(500):
            board.move_task(f"t{i:04d}", "in_progress")
        assert board.column_size("todo") == 500
        assert board.column_size("in_progress") == 500

        # Move a quarter to done
        for i in range(250):
            board.move_task(f"t{i:04d}", "done")
        assert board.column_size("done") == 250

    def test_1000_stage_pipeline(self) -> None:
        p = Pipeline(name="stress")
        # 1000 independent stages
        for i in range(1000):
            p.add_stage(f"s{i:04d}", "agent", depends_on=[])
        order = p.topological_sort()
        assert len(order) == 1000


# ===================================================================
# Dependency Cycle Detection Tests
# ===================================================================


class TestCycleDetection:
    def test_simple_cycle(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", depends_on=["b"])
        p.add_stage("b", "agent", depends_on=["a"])
        with pytest.raises(RuntimeError, match="Cycle"):
            p.topological_sort()

    def test_self_cycle(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", depends_on=["a"])
        with pytest.raises(RuntimeError, match="Cycle"):
            p.topological_sort()

    def test_long_cycle(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", depends_on=["e"])
        p.add_stage("b", "agent", depends_on=["a"])
        p.add_stage("c", "agent", depends_on=["b"])
        p.add_stage("d", "agent", depends_on=["c"])
        p.add_stage("e", "agent", depends_on=["d"])
        with pytest.raises(RuntimeError, match="Cycle"):
            p.topological_sort()

    def test_no_false_positive(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", depends_on=[])
        p.add_stage("b", "agent", depends_on=["a"])
        p.add_stage("c", "agent", depends_on=["b"])
        # No cycle here
        order = p.topological_sort()
        assert order == ["a", "b", "c"]


# ===================================================================
# Integration Tests
# ===================================================================


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_pipeline_lifecycle(self) -> None:
        """Integration test: create -> run -> check board -> export."""
        engine = OrchestratorEngine()

        # Create pipeline
        pipeline = engine.create_pipeline(
            "integration-test",
            stages=[
                {
                    "name": "fetch",
                    "agent_type": "pass-through",
                    "input_keys": ["source"],
                    "output_keys": ["raw"],
                    "depends_on": [],
                },
                {
                    "name": "process",
                    "agent_type": "pass-through",
                    "input_keys": ["raw"],
                    "output_keys": ["processed"],
                    "depends_on": ["fetch"],
                },
            ],
        )
        assert pipeline.name == "integration-test"
        assert len(pipeline.stages) == 2

        # Run pipeline
        result = await engine.run("integration-test", inputs={"source": "data"})
        assert "raw" in result
        assert "processed" in result

        # Check board
        board = engine.get_board("integration-test")
        state = board.get_board_state()
        assert len(state["done"]) == 2

        # Export YAML
        yaml_str = pipeline.to_yaml()
        assert "integration-test" in yaml_str
        assert "fetch" in yaml_str
        assert "process" in yaml_str
