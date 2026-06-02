"""Tests for KanbanBoard and Task classes."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agentix.kanban import KanbanBoard, Task, TaskStatus, is_valid_transition
from agentix.priority import Priority

class TestTaskBasics:
    def test_default_status(self):
        assert Task().status == TaskStatus.TODO

    def test_default_priority(self):
        assert Task().priority == Priority.MEDIUM

    def test_auto_id(self):
        assert len(Task(title="x").id) == 12

    def test_update_status(self):
        t = Task()
        t.update_status(TaskStatus.IN_PROGRESS)
        assert t.status == TaskStatus.IN_PROGRESS

    def test_invalid_transition_raises(self):
        t = Task()
        with pytest.raises(ValueError, match="Invalid"):
            t.update_status(TaskStatus.DONE)

    def test_assign(self):
        t = Task()
        t.assign("alice")
        assert t.assignee == "alice"

class TestStatusTransitions:
    def test_todo_to_in_progress(self):
        assert is_valid_transition("todo", "in_progress")

    def test_todo_to_done_invalid(self):
        assert not is_valid_transition("todo", "done")

    def test_in_progress_to_done(self):
        assert is_valid_transition("in_progress", "done")

    def test_review_to_in_progress(self):
        assert is_valid_transition("review", "in_progress")

    def test_done_is_final(self):
        assert not is_valid_transition("done", "todo")

class TestKanbanBoard:
    def test_add_task(self):
        b = KanbanBoard("test")
        b.add_task(Task(id="t1"))
        assert b.column_size("todo") == 1

    def test_add_to_custom_column(self):
        b = KanbanBoard("test")
        b.add_task(Task(id="t1"), column="in_progress")
        assert b.column_size("in_progress") == 1

    def test_move_task(self):
        b = KanbanBoard("test")
        b.add_task(Task(id="t1"))
        b.move_task("t1", "done")
        assert b.column_size("done") == 1

    def test_remove_task(self):
        b = KanbanBoard("test")
        b.add_task(Task(id="t1"))
        assert b.remove_task("t1").id == "t1"

    def test_clear(self):
        b = KanbanBoard("test")
        b.add_task(Task(id="t1"))
        b.add_task(Task(id="t2"))
        b.clear()
        assert b.column_size("todo") == 0

    def test_empty_board_state(self):
        state = KanbanBoard("empty").get_board_state()
        assert state == {"todo": [], "in_progress": [], "review": [], "done": []}

    def test_tasks_by_agent(self):
        b = KanbanBoard("test")
        b.add_task(Task(id="t1", agent="codex"))
        assert len(b.tasks_by_agent("codex")) == 1

    def test_tasks_by_assignee(self):
        b = KanbanBoard("test")
        b.add_task(Task(id="t1", assignee="alice"))
        assert len(b.tasks_by_assignee("alice")) == 1

    def test_sorted_by_priority(self):
        b = KanbanBoard("test")
        b.add_task(Task(id="t1", priority=Priority.CRITICAL))
        b.add_task(Task(id="t2", priority=Priority.LOW))
        sorted_ = b.get_tasks_sorted_by_priority()
        assert sorted_[0].priority == Priority.CRITICAL

    def test_stress_1000_tasks(self):
        b = KanbanBoard("stress")
        for i in range(1000):
            b.add_task(Task(id=f"t{i:04d}"))
        assert b.column_size("todo") == 1000
