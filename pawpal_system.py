"""
PawPal+ — Backend Logic Layer
pawpal_system.py

All domain classes live here. The Streamlit UI (app.py) imports from this module.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Priority ordering (used by the scheduler)
# ---------------------------------------------------------------------------
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# Valid task categories
TASK_CATEGORIES = {"walk", "feeding", "medication", "grooming", "enrichment", "vet", "other"}

# Valid recurrence frequencies
RECURRENCE_OPTIONS = {"daily", "weekly", "none"}


# ---------------------------------------------------------------------------
# Task — a single care item for a pet
# ---------------------------------------------------------------------------
@dataclass
class Task:
    """Represents one pet-care activity."""

    title: str
    category: str = "other"
    duration_minutes: int = 15
    priority: str = "medium"          # "high" | "medium" | "low"
    is_recurring: bool = False
    recurrence_frequency: str = "none"  # "daily" | "weekly" | "none"
    is_completed: bool = False
    scheduled_time: Optional[datetime] = None
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def complete(self) -> None:
        """Mark this task as done."""
        self.is_completed = True

    def reschedule(self, new_time: datetime) -> None:
        """Move the task to a new start time."""
        self.scheduled_time = new_time

    def next_occurrence(self) -> Optional["Task"]:
        """
        For recurring tasks, return a *new* Task instance scheduled for the
        next occurrence (today + 1 day for daily, + 7 days for weekly).
        Returns None if the task is not recurring.

        The new instance starts as incomplete so it will be picked up by
        the next call to get_pending_tasks().
        """
        if not self.is_recurring or self.recurrence_frequency == "none":
            return None

        base = self.scheduled_time or datetime.now()
        delta = timedelta(days=1) if self.recurrence_frequency == "daily" else timedelta(weeks=1)
        return Task(
            title=self.title,
            category=self.category,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            is_recurring=self.is_recurring,
            recurrence_frequency=self.recurrence_frequency,
            is_completed=False,
            scheduled_time=base + delta,
        )

    def __post_init__(self) -> None:
        if self.priority not in PRIORITY_ORDER:
            raise ValueError(f"priority must be one of {list(PRIORITY_ORDER.keys())}")
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")


# ---------------------------------------------------------------------------
# Pet — one animal belonging to an owner
# ---------------------------------------------------------------------------
@dataclass
class Pet:
    """Represents a pet with its associated tasks."""

    name: str
    species: str = "dog"
    breed: str = "unknown"
    age_years: int = 1
    tasks: list[Task] = field(default_factory=list)
    pet_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def add_task(self, task: Task) -> None:
        """Attach a task to this pet."""
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> bool:
        """Remove a task by ID. Returns True if found and removed."""
        original_len = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.task_id != task_id]
        return len(self.tasks) < original_len

    def get_tasks(self) -> list[Task]:
        """Return all tasks."""
        return list(self.tasks)

    def get_pending_tasks(self) -> list[Task]:
        """Return only tasks that haven't been completed yet."""
        return [t for t in self.tasks if not t.is_completed]


# ---------------------------------------------------------------------------
# Owner — the human responsible for pet care
# ---------------------------------------------------------------------------
@dataclass
class Owner:
    """Represents a pet owner."""

    name: str
    email: str = ""
    available_minutes_per_day: int = 120   # default 2 hours of care time
    pets: list[Pet] = field(default_factory=list)
    owner_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def remove_pet(self, pet_id: str) -> bool:
        """Unregister a pet by ID. Returns True if found and removed."""
        original_len = len(self.pets)
        self.pets = [p for p in self.pets if p.pet_id != pet_id]
        return len(self.pets) < original_len

    def get_pets(self) -> list[Pet]:
        """Return all pets."""
        return list(self.pets)


# ---------------------------------------------------------------------------
# ScheduledBlock — one time-slot in the final plan
# ---------------------------------------------------------------------------
@dataclass
class ScheduledBlock:
    """A concrete time slot assigned to a task in the daily schedule."""

    task: Task
    start_time: datetime
    reason: str = ""

    @property
    def end_time(self) -> datetime:
        return self.start_time + timedelta(minutes=self.task.duration_minutes)

    def duration(self) -> int:
        """Duration of this block in minutes."""
        return self.task.duration_minutes

    def overlaps_with(self, other: "ScheduledBlock") -> bool:
        """Return True if this block overlaps with another."""
        return self.start_time < other.end_time and other.start_time < self.end_time

    def __str__(self) -> str:
        return (
            f"{self.start_time.strftime('%H:%M')}–{self.end_time.strftime('%H:%M')} "
            f"| {self.task.title} ({self.task.duration_minutes} min) "
            f"[{self.task.priority}]"
        )


# ---------------------------------------------------------------------------
# Scheduler — the brain that builds the daily plan
# ---------------------------------------------------------------------------
class Scheduler:
    """
    Builds a conflict-free daily schedule for one pet.

    Algorithm (greedy, priority-first):
    1. Collect pending tasks for the pet.
    2. Sort by priority (high → medium → low); ties broken by duration (shorter first).
    3. Walk through tasks in order; assign the next available time slot.
    4. Stop when no more time is available within the day window.
    """

    def __init__(
        self,
        owner: Owner,
        pet: Pet,
        day_start_hour: int = 7,
        day_end_hour: int = 21,
    ) -> None:
        self.owner = owner
        self.pet = pet
        self.day_start_hour = day_start_hour
        self.day_end_hour = day_end_hour
        self.schedule: list[ScheduledBlock] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_schedule(self, reference_date: Optional[datetime] = None) -> list[ScheduledBlock]:
        """
        Generate an ordered, conflict-free schedule for the day.

        Args:
            reference_date: The date to schedule for (defaults to today).

        Returns:
            A list of ScheduledBlock objects in chronological order.
        """
        if reference_date is None:
            reference_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        day_start = reference_date.replace(hour=self.day_start_hour, minute=0)
        day_end = reference_date.replace(hour=self.day_end_hour, minute=0)

        pending = self.pet.get_pending_tasks()
        sorted_tasks = self.sort_tasks_by_priority(pending)
        filtered = self.filter_by_available_time(sorted_tasks)

        self.schedule = []
        current_time = day_start

        for task in filtered:
            block_end = current_time + timedelta(minutes=task.duration_minutes)
            if block_end > day_end:
                break  # No more room in the day

            reason = self._build_reason(task)
            block = ScheduledBlock(task=task, start_time=current_time, reason=reason)
            self.schedule.append(block)
            current_time = block_end  # Advance the clock

        return self.schedule

    def sort_tasks_by_priority(self, tasks: list[Task]) -> list[Task]:
        """
        Sort tasks: high → medium → low.
        Within the same priority, shorter tasks come first (quick wins).
        """
        return sorted(
            tasks,
            key=lambda t: (PRIORITY_ORDER[t.priority], t.duration_minutes),
        )

    def filter_by_available_time(self, tasks: list[Task]) -> list[Task]:
        """
        Return only as many tasks as fit within the owner's daily available minutes.
        Assumes tasks are already sorted in desired execution order.
        """
        result: list[Task] = []
        total = 0
        for task in tasks:
            if total + task.duration_minutes <= self.owner.available_minutes_per_day:
                result.append(task)
                total += task.duration_minutes
        return result

    def detect_conflicts(self, blocks: Optional[list[ScheduledBlock]] = None) -> list[tuple[ScheduledBlock, ScheduledBlock]]:
        """
        Find any overlapping time blocks.

        Returns a list of (block_a, block_b) pairs that overlap.
        The schedule produced by build_schedule() is always conflict-free;
        this method is useful for validating externally constructed schedules.
        """
        blocks = blocks or self.schedule
        conflicts: list[tuple[ScheduledBlock, ScheduledBlock]] = []
        for i, a in enumerate(blocks):
            for b in blocks[i + 1 :]:
                if a.overlaps_with(b):
                    conflicts.append((a, b))
        return conflicts

    def get_recurring_tasks(self) -> list[Task]:
        """Return all recurring tasks assigned to this pet."""
        return [t for t in self.pet.get_tasks() if t.is_recurring]

    def sort_by_time(self, tasks: Optional[list[Task]] = None) -> list[Task]:
        """
        Sort tasks by their scheduled_time (earliest first).
        Tasks without a scheduled_time are placed at the end.

        Uses a lambda key so that None times sort after all real datetimes,
        avoiding a TypeError when mixing datetime and None.

        Args:
            tasks: List to sort. Defaults to all tasks on the pet.

        Returns:
            A new sorted list (original is not mutated).
        """
        source = tasks if tasks is not None else self.pet.get_tasks()
        return sorted(
            source,
            key=lambda t: (t.scheduled_time is None, t.scheduled_time or datetime.min),
        )

    @staticmethod
    def filter_tasks(
        tasks: list[Task],
        *,
        completed: Optional[bool] = None,
        pet_name: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> list[Task]:
        """
        Filter a flat list of tasks by one or more optional criteria.

        All supplied criteria are combined with AND logic — a task must
        satisfy every non-None criterion to be included.

        Args:
            tasks:     Source list to filter (not mutated).
            completed: If True, keep only completed tasks; if False, keep only
                       pending tasks; if None, no completion filter is applied.
            pet_name:  Case-insensitive substring match on task title prefix
                       (tasks don't store a back-reference to their pet, so
                       callers should pass the tasks of a specific pet when
                       filtering by name makes sense).
            category:  Exact match on task.category (e.g. "walk", "feeding").
            priority:  Exact match on task.priority ("high", "medium", "low").

        Returns:
            A new list containing only the matching tasks.
        """
        result = tasks
        if completed is not None:
            result = [t for t in result if t.is_completed == completed]
        if pet_name is not None:
            result = [t for t in result if pet_name.lower() in t.title.lower()]
        if category is not None:
            result = [t for t in result if t.category == category]
        if priority is not None:
            result = [t for t in result if t.priority == priority]
        return result

    def mark_task_complete(self, task: Task) -> Optional[Task]:
        """
        Mark a task complete and, if it is recurring, automatically create
        the next occurrence and attach it to the same pet.

        This is the preferred way to complete tasks — it handles the
        recurring-task lifecycle in one call instead of requiring callers
        to manage next_occurrence() manually.

        Args:
            task: The Task to complete. Must already belong to self.pet.

        Returns:
            The newly created next-occurrence Task, or None if the task
            is not recurring.
        """
        task.complete()
        next_task = task.next_occurrence()
        if next_task is not None:
            self.pet.add_task(next_task)
        return next_task

    def conflict_warnings(
        self, blocks: Optional[list[ScheduledBlock]] = None
    ) -> list[str]:
        """
        Return human-readable warning strings for any overlapping blocks,
        rather than raising an exception.

        Lightweight strategy: O(n²) pairwise overlap check. Suitable for
        typical daily schedules (< 20 tasks per pet).

        Args:
            blocks: Blocks to check. Defaults to self.schedule.

        Returns:
            A list of warning strings. Empty list means no conflicts.
        """
        pairs = self.detect_conflicts(blocks)
        warnings: list[str] = []
        for a, b in pairs:
            warnings.append(
                f"⚠ Conflict: '{a.task.title}' "
                f"({a.start_time.strftime('%H:%M')}–{a.end_time.strftime('%H:%M')}) "
                f"overlaps with '{b.task.title}' "
                f"({b.start_time.strftime('%H:%M')}–{b.end_time.strftime('%H:%M')})"
            )
        return warnings

    def explain_plan(self) -> str:
        """
        Return a human-readable explanation of the generated schedule.
        Call build_schedule() first.
        """
        if not self.schedule:
            return "No schedule has been generated yet. Call build_schedule() first."

        lines = [
            f"Daily plan for {self.pet.name} ({self.pet.species}) — "
            f"owner: {self.owner.name}",
            "-" * 60,
        ]
        for block in self.schedule:
            lines.append(f"  {block}  ← {block.reason}")

        total_mins = sum(b.duration() for b in self.schedule)
        lines.append("-" * 60)
        lines.append(
            f"Total scheduled: {total_mins} min  "
            f"(owner budget: {self.owner.available_minutes_per_day} min)"
        )
        skipped = [
            t for t in self.pet.get_pending_tasks()
            if t not in [b.task for b in self.schedule]
        ]
        if skipped:
            lines.append(f"Skipped ({len(skipped)} tasks — insufficient time or budget):")
            for t in skipped:
                lines.append(f"  • {t.title} [{t.priority}] ({t.duration_minutes} min)")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_reason(self, task: Task) -> str:
        """Generate a one-line explanation for why this task was scheduled."""
        if task.priority == "high":
            return "High priority — scheduled first."
        if task.is_recurring:
            return f"Recurring ({task.recurrence_frequency}) task — included automatically."
        return f"Medium/low priority task — fits within available time."
