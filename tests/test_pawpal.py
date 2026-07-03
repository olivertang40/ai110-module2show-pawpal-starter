"""
tests/test_pawpal.py — Automated test suite for PawPal+

Run:  python -m pytest tests/ -v
"""

import pytest
from datetime import datetime, timedelta

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


# ─────────────────────────────────────────────────────────────────────────────
# Algorithm layer tests (Phase 4)
# ─────────────────────────────────────────────────────────────────────────────

class TestSortByTime:
    _today = datetime(2026, 7, 3)

    def test_sort_by_time_orders_correctly(self, sample_owner, sample_pet):
        """sort_by_time() must return tasks in ascending scheduled_time order."""
        late   = Task("Late",   duration_minutes=10, priority="low",    scheduled_time=self._today.replace(hour=18))
        early  = Task("Early",  duration_minutes=10, priority="high",   scheduled_time=self._today.replace(hour=8))
        midday = Task("Midday", duration_minutes=10, priority="medium", scheduled_time=self._today.replace(hour=12))
        for t in [late, early, midday]:
            sample_pet.add_task(t)
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)
        result = sched.sort_by_time()
        times = [t.scheduled_time for t in result if t.scheduled_time]
        assert times == sorted(times)

    def test_sort_by_time_puts_none_last(self, sample_owner, sample_pet):
        """Tasks without a scheduled_time must appear after timed tasks."""
        timed = Task("Timed",   duration_minutes=10, priority="low",    scheduled_time=self._today.replace(hour=9))
        untimed = Task("Untimed", duration_minutes=10, priority="high")  # no scheduled_time
        sample_pet.add_task(untimed)
        sample_pet.add_task(timed)
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)
        result = sched.sort_by_time()
        assert result[-1].scheduled_time is None


class TestFilterTasks:
    def _tasks(self):
        return [
            Task("Walk A",   category="walk",      duration_minutes=30, priority="high"),
            Task("Feed B",   category="feeding",   duration_minutes=10, priority="high"),
            Task("Play C",   category="enrichment",duration_minutes=20, priority="medium"),
            Task("Groom D",  category="grooming",  duration_minutes=15, priority="low"),
        ]

    def test_filter_by_category(self):
        """filter_tasks(category='walk') must return only walk tasks."""
        result = Scheduler.filter_tasks(self._tasks(), category="walk")
        assert all(t.category == "walk" for t in result)
        assert len(result) == 1

    def test_filter_by_priority(self):
        """filter_tasks(priority='high') must return only high-priority tasks."""
        result = Scheduler.filter_tasks(self._tasks(), priority="high")
        assert all(t.priority == "high" for t in result)
        assert len(result) == 2

    def test_filter_completed_false(self):
        """filter_tasks(completed=False) must exclude completed tasks."""
        tasks = self._tasks()
        tasks[0].complete()
        result = Scheduler.filter_tasks(tasks, completed=False)
        assert all(not t.is_completed for t in result)
        assert len(result) == 3

    def test_filter_completed_true(self):
        """filter_tasks(completed=True) must return only completed tasks."""
        tasks = self._tasks()
        tasks[1].complete()
        result = Scheduler.filter_tasks(tasks, completed=True)
        assert all(t.is_completed for t in result)
        assert len(result) == 1

    def test_filter_combined(self):
        """Multiple filter criteria must be AND-combined."""
        tasks = self._tasks()
        tasks[0].complete()   # Walk A — high, walk, complete
        result = Scheduler.filter_tasks(tasks, completed=True, priority="high")
        assert len(result) == 1
        assert result[0].title == "Walk A"


class TestRecurringTaskRenewal:
    def test_next_occurrence_daily(self):
        """next_occurrence() for a daily task must be scheduled +1 day ahead."""
        base_time = datetime(2026, 7, 3, 8, 0)
        t = Task("Morning walk", is_recurring=True, recurrence_frequency="daily",
                 duration_minutes=30, priority="high", scheduled_time=base_time)
        nxt = t.next_occurrence()
        assert nxt is not None
        assert nxt.scheduled_time == base_time + timedelta(days=1)
        assert nxt.is_completed is False

    def test_next_occurrence_weekly(self):
        """next_occurrence() for a weekly task must be scheduled +7 days ahead."""
        base_time = datetime(2026, 7, 3, 10, 0)
        t = Task("Flea treatment", is_recurring=True, recurrence_frequency="weekly",
                 duration_minutes=10, priority="medium", scheduled_time=base_time)
        nxt = t.next_occurrence()
        assert nxt is not None
        assert nxt.scheduled_time == base_time + timedelta(weeks=1)

    def test_next_occurrence_non_recurring_returns_none(self):
        """next_occurrence() on a non-recurring task must return None."""
        t = Task("One-off task", is_recurring=False, duration_minutes=10, priority="low")
        assert t.next_occurrence() is None

    def test_mark_task_complete_adds_new_task(self, sample_owner, sample_pet):
        """mark_task_complete() on a recurring task must add a new task to the pet."""
        recurring = Task("Daily walk", is_recurring=True, recurrence_frequency="daily",
                         duration_minutes=30, priority="high",
                         scheduled_time=datetime(2026, 7, 3, 7, 0))
        sample_pet.add_task(recurring)
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)

        before_count = len(sample_pet.get_tasks())
        next_task = sched.mark_task_complete(recurring)

        assert recurring.is_completed is True
        assert next_task is not None
        assert len(sample_pet.get_tasks()) == before_count + 1
        assert next_task in sample_pet.get_tasks()

    def test_mark_task_complete_non_recurring_no_new_task(self, sample_owner, sample_pet):
        """mark_task_complete() on a non-recurring task must not add any new task."""
        one_off = Task("One-off groom", is_recurring=False, duration_minutes=15, priority="low")
        sample_pet.add_task(one_off)
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)

        before_count = len(sample_pet.get_tasks())
        result = sched.mark_task_complete(one_off)

        assert one_off.is_completed is True
        assert result is None
        assert len(sample_pet.get_tasks()) == before_count  # no new task added


class TestConflictWarnings:
    _today = datetime(2026, 7, 3)

    def test_warnings_on_overlap(self, sample_owner, sample_pet):
        """conflict_warnings() must return a non-empty list when blocks overlap."""
        t1 = Task("Task A", duration_minutes=60, priority="high")
        t2 = Task("Task B", duration_minutes=30, priority="medium")
        start = self._today.replace(hour=10)
        b1 = ScheduledBlock(task=t1, start_time=start)
        b2 = ScheduledBlock(task=t2, start_time=start + timedelta(minutes=30))  # inside b1
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)
        warnings = sched.conflict_warnings([b1, b2])
        assert len(warnings) == 1
        assert "Conflict" in warnings[0]

    def test_no_warnings_when_sequential(self, sample_owner, sample_pet):
        """conflict_warnings() must return [] for back-to-back non-overlapping blocks."""
        t1 = Task("Task A", duration_minutes=30, priority="high")
        t2 = Task("Task B", duration_minutes=30, priority="medium")
        start = self._today.replace(hour=10)
        b1 = ScheduledBlock(task=t1, start_time=start)
        b2 = ScheduledBlock(task=t2, start_time=start + timedelta(minutes=30))
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)
        assert sched.conflict_warnings([b1, b2]) == []

    def test_warnings_are_strings(self, sample_owner, sample_pet):
        """Each warning returned must be a plain string."""
        t1 = Task("A", duration_minutes=60, priority="high")
        t2 = Task("B", duration_minutes=60, priority="high")
        start = self._today.replace(hour=9)
        b1 = ScheduledBlock(task=t1, start_time=start)
        b2 = ScheduledBlock(task=t2, start_time=start)
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)
        warnings = sched.conflict_warnings([b1, b2])
        assert all(isinstance(w, str) for w in warnings)


# ─────────────────────────────────────────────────────────────────────────────
# Edge-case / boundary tests (Phase 5)
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Boundary and edge-case scenarios identified during Phase 5 review."""

    _today = datetime(2026, 7, 3)

    # ── Scheduler edge cases ─────────────────────────────────────────────────

    def test_all_tasks_completed_gives_empty_schedule(self, sample_owner, sample_pet):
        """If every task is already complete, the schedule must be empty."""
        for i in range(3):
            t = Task(f"Task {i}", duration_minutes=10, priority="medium")
            t.complete()
            sample_pet.add_task(t)
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)
        blocks = sched.build_schedule(self._today)
        assert blocks == []

    def test_budget_exactly_equals_task_total(self, sample_owner, sample_pet):
        """When task durations sum exactly to the budget, all tasks are scheduled."""
        sample_owner.available_minutes_per_day = 30
        # Two tasks that together equal the budget exactly
        sample_pet.add_task(Task("A", duration_minutes=20, priority="medium"))
        sample_pet.add_task(Task("B", duration_minutes=10, priority="medium"))
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)
        blocks = sched.build_schedule(self._today)
        total = sum(b.duration() for b in blocks)
        assert total == 30
        assert len(blocks) == 2

    def test_single_task_fills_day_window(self, sample_owner, sample_pet):
        """A task that exactly fills the day window (start→end) must be scheduled."""
        # 7:00–21:00 = 840 min window, but budget caps it; test the window boundary
        sample_owner.available_minutes_per_day = 840
        sample_pet.add_task(Task("Full day task", duration_minutes=840, priority="high"))
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet, day_start_hour=7, day_end_hour=21)
        blocks = sched.build_schedule(self._today)
        assert len(blocks) == 1
        assert blocks[0].end_time == self._today.replace(hour=21, minute=0)

    def test_task_one_minute_over_window_is_skipped(self, sample_owner, sample_pet):
        """A task ending 1 minute past day_end must not be scheduled."""
        sample_owner.available_minutes_per_day = 900
        # 841 min starting at 07:00 would end at 21:01, past the 21:00 boundary
        sample_pet.add_task(Task("Overlong task", duration_minutes=841, priority="high"))
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet, day_start_hour=7, day_end_hour=21)
        blocks = sched.build_schedule(self._today)
        assert blocks == []

    def test_same_priority_shorter_task_scheduled_first(self, sample_owner, sample_pet):
        """Among tasks with the same priority, the shorter one must come first."""
        sample_pet.add_task(Task("Long high",  duration_minutes=45, priority="high"))
        sample_pet.add_task(Task("Short high", duration_minutes=10, priority="high"))
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)
        blocks = sched.build_schedule(self._today)
        assert blocks[0].task.title == "Short high"
        assert blocks[1].task.title == "Long high"

    def test_medium_before_low_in_schedule(self, sample_owner, sample_pet):
        """Medium-priority tasks must be scheduled before low-priority tasks."""
        sample_pet.add_task(Task("Low task",    duration_minutes=10, priority="low"))
        sample_pet.add_task(Task("Medium task", duration_minutes=10, priority="medium"))
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)
        blocks = sched.build_schedule(self._today)
        priorities = [b.task.priority for b in blocks]
        med_idx = priorities.index("medium")
        low_idx = priorities.index("low")
        assert med_idx < low_idx

    def test_schedule_blocks_are_chronological(self, sample_owner, sample_pet):
        """Every block's start_time must be >= the previous block's end_time."""
        for i in range(5):
            sample_pet.add_task(Task(f"Task {i}", duration_minutes=15, priority="medium"))
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)
        blocks = sched.build_schedule(self._today)
        for i in range(1, len(blocks)):
            assert blocks[i].start_time >= blocks[i - 1].end_time

    def test_explain_plan_before_build_returns_message(self, sample_owner, sample_pet):
        """explain_plan() called before build_schedule() must return a guidance string."""
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)
        msg = sched.explain_plan()
        assert "build_schedule" in msg or "No schedule" in msg

    def test_schedule_start_time_matches_day_start(self, sample_owner, sample_pet):
        """The first scheduled block must start exactly at day_start_hour."""
        sample_pet.add_task(Task("First task", duration_minutes=10, priority="high"))
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet, day_start_hour=8)
        blocks = sched.build_schedule(self._today)
        assert blocks[0].start_time.hour == 8
        assert blocks[0].start_time.minute == 0

    # ── Recurring task edge cases ────────────────────────────────────────────

    def test_next_occurrence_inherits_properties(self):
        """The next occurrence must have the same title, category, priority, and duration."""
        original = Task(
            "Heartworm med",
            category="medication",
            duration_minutes=5,
            priority="high",
            is_recurring=True,
            recurrence_frequency="daily",
            scheduled_time=datetime(2026, 7, 3, 8, 0),
        )
        nxt = original.next_occurrence()
        assert nxt is not None
        assert nxt.title == original.title
        assert nxt.category == original.category
        assert nxt.duration_minutes == original.duration_minutes
        assert nxt.priority == original.priority
        assert nxt.is_recurring is True
        assert nxt.recurrence_frequency == original.recurrence_frequency

    def test_next_occurrence_has_new_id(self):
        """The next occurrence must have a different task_id from the original."""
        t = Task(
            "Daily walk",
            is_recurring=True,
            recurrence_frequency="daily",
            duration_minutes=30,
            priority="high",
            scheduled_time=datetime(2026, 7, 3, 7, 0),
        )
        nxt = t.next_occurrence()
        assert nxt is not None
        assert nxt.task_id != t.task_id

    def test_completing_recurring_task_is_removed_from_pending(self, sample_owner, sample_pet):
        """After mark_task_complete(), the original task must not appear in get_pending_tasks()."""
        recurring = Task(
            "Daily feed",
            is_recurring=True,
            recurrence_frequency="daily",
            duration_minutes=10,
            priority="high",
            scheduled_time=datetime(2026, 7, 3, 7, 0),
        )
        sample_pet.add_task(recurring)
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)
        sched.mark_task_complete(recurring)
        pending_ids = [t.task_id for t in sample_pet.get_pending_tasks()]
        assert recurring.task_id not in pending_ids

    # ── Conflict detection edge cases ────────────────────────────────────────

    def test_multiple_conflicts_all_reported(self, sample_owner, sample_pet):
        """When three blocks all overlap, conflict_warnings() must report all pairs."""
        start = self._today.replace(hour=10)
        t1 = Task("A", duration_minutes=60, priority="high")
        t2 = Task("B", duration_minutes=60, priority="high")
        t3 = Task("C", duration_minutes=60, priority="high")
        b1 = ScheduledBlock(task=t1, start_time=start)
        b2 = ScheduledBlock(task=t2, start_time=start)  # overlaps b1
        b3 = ScheduledBlock(task=t3, start_time=start)  # overlaps b1 and b2
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)
        warnings = sched.conflict_warnings([b1, b2, b3])
        # 3 blocks all at same start → 3 pairs: (b1,b2), (b1,b3), (b2,b3)
        assert len(warnings) == 3

    def test_adjacent_blocks_do_not_conflict(self, sample_owner, sample_pet):
        """Blocks that share an endpoint (one ends exactly when the next starts) must not conflict."""
        start = self._today.replace(hour=10)
        t1 = Task("A", duration_minutes=30, priority="high")
        t2 = Task("B", duration_minutes=30, priority="high")
        b1 = ScheduledBlock(task=t1, start_time=start)               # 10:00–10:30
        b2 = ScheduledBlock(task=t2, start_time=start + timedelta(minutes=30))  # 10:30–11:00
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)
        assert sched.conflict_warnings([b1, b2]) == []

    # ── Filter edge cases ────────────────────────────────────────────────────

    def test_filter_empty_list_returns_empty(self):
        """Filtering an empty task list must return an empty list without error."""
        assert Scheduler.filter_tasks([], priority="high") == []

    def test_filter_no_criteria_returns_all(self):
        """filter_tasks() with no criteria must return all tasks unchanged."""
        tasks = [
            Task("A", duration_minutes=10, priority="high"),
            Task("B", duration_minutes=10, priority="low"),
        ]
        assert len(Scheduler.filter_tasks(tasks)) == 2

    def test_filter_category_no_match_returns_empty(self):
        """filter_tasks() with a category that matches nothing must return []."""
        tasks = [Task("Walk", category="walk", duration_minutes=20, priority="medium")]
        assert Scheduler.filter_tasks(tasks, category="vet") == []

    # ── sort_by_time edge cases ──────────────────────────────────────────────

    def test_sort_by_time_all_none_preserves_order(self, sample_owner, sample_pet):
        """When no tasks have a scheduled_time, sort_by_time() must not raise an error."""
        for i in range(3):
            sample_pet.add_task(Task(f"Task {i}", duration_minutes=10, priority="medium"))
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)
        result = sched.sort_by_time()
        assert len(result) == 3  # just verify no crash and count is correct

    def test_sort_by_time_single_task(self, sample_owner, sample_pet):
        """sort_by_time() on a one-task pet must return a list with exactly that task."""
        t = Task("Only task", duration_minutes=10, priority="high",
                 scheduled_time=self._today.replace(hour=9))
        sample_pet.add_task(t)
        sample_owner.add_pet(sample_pet)
        sched = Scheduler(owner=sample_owner, pet=sample_pet)
        result = sched.sort_by_time()
        assert result == [t]
