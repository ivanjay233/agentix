"""
Tests for agentix core components.
"""

import asyncio
import os
import sys
import tempfile

import pytest

# Ensure the package root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agentix.core import OrchestratorEngine
from agentix.pipeline import Pipeline
from agentix.kanban import KanbanBoard, Task, TaskStatus
from agentix.agents.base import BaseAgent
from agentix.agents.codex_agent import CodexAgent
from agentix.agents.review_agent import ReviewAgent


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

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

    def test_add_duplicate_stage_raises(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("write", "codex")
        with pytest.raises(ValueError):
            p.add_stage("write", "codex")

    def test_remove_stage(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("write", "codex")
        p.remove_stage("write")
        assert len(p.stages) == 0

    def test_remove_missing_stage_raises(self) -> None:
        p = Pipeline(name="test")
        with pytest.raises(KeyError):
            p.remove_stage("nonexistent")

    def test_get_stage(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("write", "codex")
        s = p.get_stage("write")
        assert s["agent_type"] == "codex"

    def test_topological_sort_linear(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", depends_on=[])
        p.add_stage("b", "agent", depends_on=["a"])
        p.add_stage("c", "agent", depends_on=["b"])
        assert p.topological_sort() == ["a", "b", "c"]

    def test_topological_sort_cycle_raises(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("a", "agent", depends_on=["c"])
        p.add_stage("b", "agent", depends_on=["a"])
        p.add_stage("c", "agent", depends_on=["b"])
        with pytest.raises(RuntimeError, match="Cycle"):
            p.topological_sort()

    def test_yaml_roundtrip(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("write", "codex", input_keys=["topic"], output_keys=["draft"])
        p.add_stage("review", "review_agent", depends_on=["write"])
        yaml_str = p.to_yaml()
        p2 = Pipeline.from_yaml(yaml_str)
        assert p2.name == p.name
        assert len(p2.stages) == len(p.stages)
        assert p2.stages[0]["name"] == "write"

    def test_from_yaml_file(self) -> None:
        p = Pipeline(name="test")
        p.add_stage("write", "codex")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(p.to_yaml())
            f.flush()
            p2 = Pipeline.from_yaml_file(f.name)
            assert p2.name == "test"
        os.unlink(f.name)


# ---------------------------------------------------------------------------
# KanbanBoard / Task
# ---------------------------------------------------------------------------

class TestKanbanBoard:
    def test_add_task(self) -> None:
        board = KanbanBoard(name="test")
        task = Task(id="t1", title="Write docs", stage="write", agent="codex")
        board.add_task(task)
        assert board.column_size("todo") == 1

    def test_duplicate_task_raises(self) -> None:
        board = KanbanBoard(name="test")
        board.add_task(Task(id="t1"))
        with pytest.raises(ValueError):
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
        assert t.status == TaskStatus.TODO  # status not updated by move alone

    def test_remove_task(self) -> None:
        board = KanbanBoard(name="test")
        board.add_task(Task(id="t1"))
        board.remove_task("t1")
        assert board.get_task("t1") is None

    def test_get_board_state(self) -> None:
        board = KanbanBoard(name="test")
        board.add_task(Task(id="t1", title="A"))
        board.add_task(Task(id="t2", title="B"))
        state = board.get_board_state()
        assert "todo" in state
        assert len(state["todo"]) == 2

    def test_tasks_by_agent(self) -> None:
        board = KanbanBoard(name="test")
        board.add_task(Task(id="t1", agent="codex"))
        board.add_task(Task(id="t2", agent="review"))
        board.add_task(Task(id="t3", agent="codex"))
        assert len(board.tasks_by_agent("codex")) == 2
        assert len(board.tasks_by_agent("review")) == 1

    def test_invalid_column_raises(self) -> None:
        board = KanbanBoard(name="test")
        with pytest.raises(ValueError):
            board.add_task(Task(id="t1"), column="invalid")


class TestTask:
    def test_default_status(self) -> None:
        t = Task()
        assert t.status == TaskStatus.TODO

    def test_update_status(self) -> None:
        t = Task()
        t.update_status(TaskStatus.IN_PROGRESS)
        assert t.status == TaskStatus.IN_PROGRESS

    def test_to_dict(self) -> None:
        t = Task(id="abc", title="Test", stage="write", agent="codex")
        d = t.to_dict()
        assert d["id"] == "abc"
        assert d["title"] == "Test"
        assert d["status"] == "todo"


# ---------------------------------------------------------------------------
# OrchestratorEngine
# ---------------------------------------------------------------------------

class TestOrchestratorEngine:
    def test_create_pipeline(self) -> None:
        engine = OrchestratorEngine()
        p = engine.create_pipeline("test")
        assert p.name == "test"
        assert "test" in engine.list_pipelines()

    def test_duplicate_pipeline_raises(self) -> None:
        engine = OrchestratorEngine()
        engine.create_pipeline("dup")
        with pytest.raises(ValueError):
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


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

class TestBaseAgent:
    def test_abstract_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            BaseAgent()  # type: ignore[abstract]

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

    @pytest.mark.asyncio
    async def test_validate(self) -> None:
        agent = ReviewAgent()
        assert agent.validate() is True

    def test_report(self) -> None:
        agent = ReviewAgent()
        report = agent.report()
        assert "reviewed 0 task(s)" in report


class TestCodexAgent:
    @pytest.mark.asyncio
    async def test_process_mock_fallback(self) -> None:
        """When codex CLI is absent, the agent uses a mock fallback."""
        agent = CodexAgent()
        result = await agent.process({"prompt": "write hello", "language": "python"})
        assert "code" in result
        assert result["language"] == "python"

    @pytest.mark.asyncio
    async def test_process_requires_prompt(self) -> None:
        agent = CodexAgent()
        with pytest.raises(ValueError, match="prompt"):
            await agent.process({"language": "python"})

    def test_validate_no_codex(self) -> None:
        agent = CodexAgent()
        # On CI or dev machines without 'codex', this returns False
        assert agent.validate() is False  # unless codex CLI is installed

    def test_report(self) -> None:
        agent = CodexAgent()
        r = agent.report()
        assert "processed 0 task(s)" in r
