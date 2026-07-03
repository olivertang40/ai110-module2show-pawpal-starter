"""
tests/test_pawpal.py — Automated test suite for PawPal+

Run:  python -m pytest tests/ -v
"""

import pytest
from datetime import datetime

from pawpal_system import Owner, Pet, Scheduler, ScheduledBlock, Task


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures — reusable test objects
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_task() -> Task:
    return Task(title="Morning walk", category="walk", duration_minutes=30, priority="high")


@pytest.fixture
def sample_pet() -> Pet:
    return Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3)


@pytest.fixture
def sample_owner() -> Owner:
    return Owner(name="Jordan", available_minutes_per_day=120)


@pytest.fixture
def owner_with_pet(sample_owner, sample_pet) -> tuple[Owner, Pet]:
    sample_owner.add_pet(sample_pet)
    return sample_owner, sample_pet


# ─────────────────────────────────────────────────────────────────────────────
# Task tests
# ─────────────────────────────────────────────────────────────────────────────

class TestTask:
    def test_task_completion_changes_status(self, sample_task):
        """Calling complete() must flip is_completed from False to True."""
        assert sample_task.is_completed is False
        sample_task.complete()
        assert sample_task.is_completed is True

    def test_task_reschedule_updates_time(self, sample_task):
        """reschedule() must update scheduled_time to the given datetime."""
        new_time = datetime(2026, 7, 3, 9, 0)
        sample_task.reschedule(new_time)
        assert sample_task.scheduled_time == new_time

    def test_invalid_priority_raises(self):
        """Creating a Task with an invalid priority must raise ValueError."""
        with pytest.raises(ValueError, match="priority"):
            Task(title="Bad task", priority="urgent")

    def test_invalid_duration_raises(self):
        """Creating a Task with zero or negative duration must raise ValueError."""
        with pytest.raises(ValueError, match="duration_minutes"):
            Task(title="Zero task", duration_minutes=0)

    def test_task_has_unique_id(self):
        """Two separately created Tasks must have different IDs."""
        t1 = Task(title="Walk")
        t2 = Task(title="Walk")
        assert t1.task_id != t2.task_id


# ─────────────────────────────────────────────────────────────────────────────
# Pet tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPet:
    def test_add_task_increases_count(self, sample_pet, sample_task):
        """Adding a task to a Pet must increase task count by 1."""
        before = len(sample_pet.get_tasks())
        sample_pet.add_task(sample_task)
        assert len(sample_pet.get_tasks()) == before + 1

    def test_add_multiple_tasks(self, sample_pet):
        """Adding three tasks should result in a pet with exactly three tasks."""
        for i in range(3):
            sample_pet.add_task(Task(title=f"Task {i}", duration_minutes=10 + i, priority="low"))
        assert len(sample_pet.get_tasks()) == 3

    def test_remove_task_decreases_count(self, sample_pet, sample_task):
        """remove_task() must decrease task count and return True."""
        sample_pet.add_task(sample_task)
        result = sample_pet.remove_task(sample_task.task_id)
        assert result is True
        assert len(sample_pet.get_tasks()) == 0

    def test_remove_nonexistent_task_returns_false(self, sample_pet):
        """remove_task() with an unknown ID must return False without error."""
        assert sample_pet.remove_task("nonexistent-id") is False

    def test_get_pending_tasks_excludes_completed(self, sample_pet):
        """get_pending_tasks() must not return completed tasks."""
        done = Task(title="Done task", priority="low", duration_minutes=5)
        pending = Task(title="Pending task", priority="medium", duration_minutes=10)
        done.complete()
        sample_pet.add_task(done)
        sample_pet.add_task(pending)
        pending_tasks = sample_pet.get_pending_tasks()
        assert pending not in [t for t in pending_tasks if t.is_completed]
        assert all(not t.is_completed for t in pending_tasks)


# ─────────────────────────────────────────────────────────────────────────────
# Owner tests
# ─────────────────────────────────────────────────────────────────────────────

class TestOwner:
    def test_add_pet_increases_count(self, sample_owner, sample_pet):
        """Adding a pet to an Owner must increase pet count by 1."""
        before = len(sample_owner.get_pets())
        sample_owner.add_pet(sample_pet)
        assert len(sample_owner.get_pets()) == before + 1

    def test_remove_pet(self, owner_with_pet):
        """remove_pet() must remove the correct pet and return True."""
        owner, pet = owner_with_pet
        result = owner.remove_pet(pet.pet_id)
        assert result is True
        assert pet not in owner.get_pets()

    def test_remove_nonexistent_pet_returns_false(self, sample_owner):
        """remove_pet() with an unknown ID must return False."""
        assert sample_owner.remove_pet("ghost-id") is False


# ─────────────────────────────────────────────────────────────────────────────
# Scheduler tests
# ─────────────────────────────────────────────────────────────────────────────

class TestScheduler:
    _today = datetime(2026, 7, 3)

    def _make_scheduler(self, owner, pet, budget=120, start=7, end=21):
        owner.available_minutes_per_day = budget
        return Scheduler(owner=owner, pet=pet, day_start_hour=start, day_end_hour=end)

    def test_schedule_respects_priority_order(self, sample_owner, sample_pet):
        """High-priority tasks must appear before low-priority ones in the schedule."""
        sample_pet.add_task(Task("Low task",  duration_minutes=10, priority="low"))
        sample_pet.add_task(Task("High task", duration_minutes=10, priority="high"))
        sample_owner.add_pet(sample_pet)
        sched = self._make_scheduler(sample_owner, sample_pet)
        blocks = sched.build_schedule(self._today)
        priorities = [b.task.priority for b in blocks]
        high_indices = [i for i, p in enumerate(priorities) if p == "high"]
        low_indices  = [i for i, p in enumerate(priorities) if p == "low"]
        assert max(high_indices) < min(low_indices)

    def test_schedule_does_not_exceed_budget(self, sample_owner, sample_pet):
        """Total scheduled duration must not exceed the owner's available minutes."""
        for i in range(10):
            sample_pet.add_task(Task(f"Task {i}", duration_minutes=20, priority="medium"))
        sample_owner.add_pet(sample_pet)
        sched = self._make_scheduler(sample_owner, sample_pet, budget=60)
        blocks = sched.build_schedule(self._today)
        total = sum(b.duration() for b in blocks)
        assert total <= sample_owner.available_minutes_per_day

    def test_no_conflicts_in_generated_schedule(self, sample_owner, sample_pet):
        """build_schedule() must produce a conflict-free plan."""
        for i in range(5):
            sample_pet.add_task(Task(f"Task {i}", duration_minutes=15, priority="medium"))
        sample_owner.add_pet(sample_pet)
        sched = self._make_scheduler(sample_owner, sample_pet)
        sched.build_schedule(self._today)
        assert sched.detect_conflicts() == []

    def test_completed_tasks_excluded_from_schedule(self, sample_owner, sample_pet):
        """Tasks marked complete must not appear in the generated schedule."""
        done = Task("Done",    duration_minutes=10, priority="high")
        live = Task("Pending", duration_minutes=10, priority="high")
        done.complete()
        sample_pet.add_task(done)
        sample_pet.add_task(live)
        sample_owner.add_pet(sample_pet)
        sched = self._make_scheduler(sample_owner, sample_pet)
        blocks = sched.build_schedule(self._today)
        scheduled_titles = [b.task.title for b in blocks]
        assert "Done" not in scheduled_titles
        assert "Pending" in scheduled_titles

    def test_empty_task_list_gives_empty_schedule(self, sample_owner, sample_pet):
        """A pet with no tasks should produce an empty schedule."""
        sample_owner.add_pet(sample_pet)
        sched = self._make_scheduler(sample_owner, sample_pet)
        blocks = sched.build_schedule(self._today)
        assert blocks == []

    def test_task_too_long_for_budget_is_skipped(self, sample_owner, sample_pet):
        """A single task longer than the owner's budget must not be scheduled."""
        sample_pet.add_task(Task("Marathon walk", duration_minutes=200, priority="high"))
        sample_owner.available_minutes_per_day = 60
        sample_owner.add_pet(sample_pet)
        sched = self._make_scheduler(sample_owner, sample_pet, budget=60)
        blocks = sched.build_schedule(self._today)
        assert blocks == []

    def test_conflict_detection_finds_overlap(self, sample_owner, sample_pet):
        """detect_conflicts() must identify manually constructed overlapping blocks."""
        t1 = Task("Task A", duration_minutes=30, priority="high")
        t2 = Task("Task B", duration_minutes=30, priority="high")
        start = datetime(2026, 7, 3, 8, 0)
        b1 = ScheduledBlock(task=t1, start_time=start)
        b2 = ScheduledBlock(task=t2, start_time=start)  # same start = overlap
        sample_owner.add_pet(sample_pet)
        sched = self._make_scheduler(sample_owner, sample_pet)
        conflicts = sched.detect_conflicts([b1, b2])
        assert len(conflicts) == 1

    def test_explain_plan_contains_pet_name(self, sample_owner, sample_pet):
        """explain_plan() output must mention the pet's name."""
        sample_pet.add_task(Task("Walk", duration_minutes=20, priority="high"))
        sample_owner.add_pet(sample_pet)
        sched = self._make_scheduler(sample_owner, sample_pet)
        sched.build_schedule(self._today)
        explanation = sched.explain_plan()
        assert sample_pet.name in explanation
