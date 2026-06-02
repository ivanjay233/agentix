"""Integration tests for full pipeline lifecycle."""
import pytest, asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agentix.core import OrchestratorEngine
from agentix.pipeline import Pipeline
from agentix.kanban import KanbanBoard, Task
from agentix.board import BoardManager
from agentix.metrics import StageMetrics
from agentix.report import generate_pipeline_report

@pytest.mark.asyncio
class TestFullPipeline:
    async def test_create_run_check(self):
        e = OrchestratorEngine()
        e.create_pipeline("test", stages=[
            {"name": "fetch", "agent_type": "pt", "input_keys": ["src"], "output_keys": ["raw"]},
            {"name": "process", "agent_type": "pt", "input_keys": ["raw"], "output_keys": ["proc"]},
        ])
        r = await e.run("test", inputs={"src": "data"})
        assert "raw" in r and "proc" in r
        board = e.get_board("test")
        assert len(board.get_board_state()["done"]) == 2

    async def test_yaml_roundtrip(self):
        e = OrchestratorEngine()
        e.create_pipeline("test", stages=[{"name": "s1", "agent_type": "c"}])
        y = e.get_pipeline("test").to_yaml()
        assert "test" in y and "s1" in y
        p2 = Pipeline.from_yaml(y)
        assert p2.name == "test"

    async def test_board_manager(self):
        board = KanbanBoard("test")
        mgr = BoardManager(board)
        mgr.create_task("t1", "Task 1", agent="codex")
        mgr.start_task("t1")
        mgr.complete_task("t1", {"ok": True})
        stats = mgr.get_stats()
        assert stats["total_tasks"] == 1
        assert stats["by_agent"]["codex"] == 1

    async def test_metrics(self):
        metrics = StageMetrics()
        t = metrics.start_stage("s1", "codex")
        metrics.finish_stage(t)
        assert metrics.report()["total_stages"] == 1

    async def test_report_generation(self):
        p = Pipeline("test")
        p.add_stage("s1", "c")
        report = generate_pipeline_report(p)
        assert "Pipeline Report: test" in report
