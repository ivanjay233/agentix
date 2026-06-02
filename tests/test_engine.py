"""Tests for OrchestratorEngine."""
import pytest, asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agentix.core import OrchestratorEngine

class TestEnginePipelineManagement:
    def test_create_pipeline(self):
        e = OrchestratorEngine()
        p = e.create_pipeline("test")
        assert p.name == "test" and "test" in e.list_pipelines()

    def test_duplicate_raises(self):
        e = OrchestratorEngine()
        e.create_pipeline("dup")
        with pytest.raises(ValueError):
            e.create_pipeline("dup")

    def test_get_missing_raises(self):
        with pytest.raises(KeyError):
            OrchestratorEngine().get_pipeline("nope")

    def test_get_board(self):
        e = OrchestratorEngine()
        e.create_pipeline("t")
        assert e.get_board("t").name == "t_board"

    @pytest.mark.asyncio
    async def test_run(self):
        e = OrchestratorEngine()
        e.create_pipeline("t", stages=[{"name": "s1", "agent_type": "a", "output_keys": ["o"]}])
        r = await e.run("t", inputs={"i": "hello"})
        assert "o" in r

    @pytest.mark.asyncio
    async def test_run_empty(self):
        e = OrchestratorEngine()
        e.create_pipeline("empty")
        assert await e.run("empty", inputs={"k": "v"}) == {"k": "v"}

    def test_pause_resume(self):
        e = OrchestratorEngine()
        e.pause()
        assert e.is_paused()
        e.resume()
        assert not e.is_paused()

    def test_shutdown(self):
        e = OrchestratorEngine()
        e.shutdown()
        assert not e.is_running()
