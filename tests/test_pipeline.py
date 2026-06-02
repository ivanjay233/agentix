"""Tests for Pipeline class — stage management and topological sort."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agentix.pipeline import Pipeline

class TestPipelineCreation:
    def test_create_empty(self):
        p = Pipeline(name="test")
        assert p.name == "test" and p.stages == []

    def test_create_with_stages(self):
        p = Pipeline("test", stages=[{"name": "s1", "agent_type": "a"}])
        assert len(p.stages) == 1

    def test_repr(self):
        assert "Pipeline(name='test'" in repr(Pipeline("test"))

class TestStageManagement:
    def test_add_stage(self):
        p = Pipeline("test")
        p.add_stage("write", "codex", input_keys=["t"], output_keys=["d"])
        assert p.stages[0]["name"] == "write"

    def test_add_duplicate_raises(self):
        p = Pipeline("test")
        p.add_stage("s1", "a")
        with pytest.raises(ValueError, match="already exists"):
            p.add_stage("s1", "b")

    def test_remove_stage(self):
        p = Pipeline("test")
        p.add_stage("s1", "a")
        p.add_stage("s2", "b")
        p.remove_stage("s1")
        assert len(p.stages) == 1

    def test_remove_missing_raises(self):
        p = Pipeline("test")
        with pytest.raises(KeyError):
            p.remove_stage("nope")

    def test_get_stage(self):
        p = Pipeline("test")
        p.add_stage("s1", "a")
        assert p.get_stage("s1")["agent_type"] == "a"

class TestTopologicalSort:
    def test_linear(self):
        p = Pipeline("test")
        p.add_stage("a", "a", depends_on=[])
        p.add_stage("b", "a", depends_on=["a"])
        assert p.topological_sort() == ["a", "b"]

    def test_diamond(self):
        p = Pipeline("test")
        p.add_stage("a", "a")
        p.add_stage("b", "a", depends_on=["a"])
        p.add_stage("c", "a", depends_on=["a"])
        p.add_stage("d", "a", depends_on=["b", "c"])
        order = p.topological_sort()
        assert order[0] == "a" and order[-1] == "d"

    def test_parallel(self):
        p = Pipeline("test")
        p.add_stage("a", "a")
        p.add_stage("b", "a")
        assert set(p.topological_sort()) == {"a", "b"}

    def test_empty(self):
        assert Pipeline("empty").topological_sort() == []

    def test_cycle_raises(self):
        p = Pipeline("test")
        p.add_stage("a", "a", depends_on=["b"])
        p.add_stage("b", "a", depends_on=["a"])
        with pytest.raises(RuntimeError, match="Cycle"):
            p.topological_sort()

    def test_1000_stages(self):
        p = Pipeline("stress")
        for i in range(1000):
            p.add_stage(f"s{i:04d}", "agent")
        assert len(p.topological_sort()) == 1000
