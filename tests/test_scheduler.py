"""Tests for PipelineScheduler."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agentix.scheduler import PipelineScheduler
from agentix.pipeline import Pipeline

class TestSchedulerBasics:
    def test_ordered_stages(self):
        p = Pipeline("t")
        p.add_stage("a", "a")
        p.add_stage("b", "a", depends_on=["a"])
        assert PipelineScheduler(p).ordered_stages() == ["a", "b"]

    def test_ready_stages(self):
        p = Pipeline("t")
        p.add_stage("a", "a")
        p.add_stage("b", "a", depends_on=["a"])
        s = PipelineScheduler(p)
        assert s.ready_stages(set()) == ["a"]
        assert s.ready_stages({"a"}) == ["b"]

    def test_pending_stages(self):
        p = Pipeline("t")
        p.add_stage("a", "a")
        p.add_stage("b", "a")
        assert len(PipelineScheduler(p).pending_stages(set())) == 2

    def test_has_cycle(self):
        p = Pipeline("t")
        p.add_stage("a", "a", depends_on=["b"])
        p.add_stage("b", "a", depends_on=["a"])
        assert PipelineScheduler(p).has_cycle()

    def test_no_cycle(self):
        p = Pipeline("t")
        p.add_stage("a", "a")
        assert not PipelineScheduler(p).has_cycle()

    def test_critical_path(self):
        p = Pipeline("t")
        p.add_stage("a", "a")
        p.add_stage("b", "a", depends_on=["a"])
        p.add_stage("c", "a", depends_on=["b"])
        assert PipelineScheduler(p).critical_path() == 3

    def test_levels(self):
        p = Pipeline("t")
        p.add_stage("a", "a")
        p.add_stage("b", "a")
        p.add_stage("c", "a", depends_on=["a", "b"])
        levels = PipelineScheduler(p).levels()
        assert len(levels) == 2
        assert set(levels[0]) == {"a", "b"}
        assert levels[1] == ["c"]

    def test_empty_pipeline(self):
        s = PipelineScheduler(Pipeline("empty"))
        assert s.ordered_stages() == [] and s.levels() == []
