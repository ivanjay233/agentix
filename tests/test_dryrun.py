"""Tests for dry-run and validation modules."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agentix.pipeline import Pipeline
from agentix.dryrun import dry_run
from agentix.validation import validate_pipeline_config

class TestDryRun:
    def test_valid_pipeline(self):
        p = Pipeline("t")
        p.add_stage("a", "a", output_keys=["x"])
        p.add_stage("b", "a", input_keys=["x"], depends_on=["a"])
        r = dry_run(p)
        assert r.valid and r.stage_order == ["a", "b"]

    def test_missing_input_key(self):
        p = Pipeline("t")
        p.add_stage("a", "a", input_keys=["missing"])
        assert not dry_run(p).valid

    def test_cycle_detected(self):
        p = Pipeline("t")
        p.add_stage("a", "a", depends_on=["b"])
        p.add_stage("b", "a", depends_on=["a"])
        assert not dry_run(p).valid

    def test_empty_pipeline(self):
        assert not dry_run(Pipeline("empty")).valid

    def test_to_dict(self):
        d = dry_run(Pipeline("empty")).to_dict()
        assert "valid" in d and "errors" in d and "stage_order" in d

class TestValidation:
    def test_valid_config(self):
        assert validate_pipeline_config({"name": "t", "stages": [{"name": "s1", "agent_type": "c"}]}) == []

    def test_missing_name(self):
        assert any("name" in e for e in validate_pipeline_config({"stages": []}))

    def test_stages_not_list(self):
        assert any("list" in e for e in validate_pipeline_config({"name": "t", "stages": "bad"}))

    def test_empty_stages(self):
        assert any("at least one" in e for e in validate_pipeline_config({"name": "t", "stages": []}))

    def test_duplicate_stage_name(self):
        cfg = {"name": "t", "stages": [{"name": "s1", "agent_type": "a"}, {"name": "s1", "agent_type": "b"}]}
        assert any("duplicate" in e for e in validate_pipeline_config(cfg))

    def test_missing_dependency(self):
        cfg = {"name": "t", "stages": [{"name": "s1", "agent_type": "a", "depends_on": ["missing"]}]}
        assert any("depends_on" in e for e in validate_pipeline_config(cfg))
