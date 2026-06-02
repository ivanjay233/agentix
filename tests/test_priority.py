"""Tests for Priority enum."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agentix.priority import Priority

class TestPriority:
    def test_values_ordered(self):
        assert Priority.LOWEST < Priority.LOW < Priority.MEDIUM < Priority.HIGH < Priority.CRITICAL

    def test_names(self):
        assert Priority.LOWEST.name == "LOWEST"
        assert Priority.CRITICAL.name == "CRITICAL"

    def test_from_name(self):
        assert Priority["HIGH"] == Priority.HIGH

    def test_from_value(self):
        assert Priority(1) == Priority.LOWEST

    def test_in_priority_field(self):
        from agentix.kanban import Task
        t = Task(priority=Priority.CRITICAL)
        assert t.priority == Priority.CRITICAL
        assert t.to_dict()["priority"] == "CRITICAL"
