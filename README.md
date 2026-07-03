# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Run `python main.py` to see the CLI demo. Sample terminal output:

```
PawPal+ — CLI Demo  (Friday, July 03 2026)

══════════════════════════════════════════════════════════════
  🐾  Daily Plan for Mochi (dog)
  Owner: Jordan  |  Budget: 150 min
══════════════════════════════════════════════════════════════
  07:00–07:05  Heartworm med 🔁  (5 min)   [high]
    → High priority — scheduled first.
  07:05–07:15  Breakfast 🔁     (10 min)  [high]
    → High priority — scheduled first.
  07:15–07:25  Dinner 🔁        (10 min)  [high]
    → High priority — scheduled first.
  07:25–07:55  Morning walk 🔁  (30 min)  [high]
    → High priority — scheduled first.
  07:55–08:25  Evening walk 🔁  (30 min)  [high]
    → High priority — scheduled first.
  08:25–08:45  Fetch session    (20 min)  [medium]
    → Medium/low priority task — fits within available time.
  08:45–09:00  Brush coat       (15 min)  [low]
    → Medium/low priority task — fits within available time.
──────────────────────────────────────────────────────────────
  Total scheduled : 120 min
  Owner budget    : 150 min
══════════════════════════════════════════════════════════════

  ✔  No scheduling conflicts.

══════════════════════════════════════════════════════════════
  🐾  Daily Plan for Luna (cat)
  Owner: Jordan  |  Budget: 150 min
══════════════════════════════════════════════════════════════
  07:00–07:05  Litter box 🔁       (5 min)   [high]
  07:05–07:15  Morning feeding 🔁  (10 min)  [high]
  07:15–07:25  Evening feeding 🔁  (10 min)  [high]
  07:25–07:35  Flea treatment 🔁   (10 min)  [medium]
  07:35–07:50  Laser play          (15 min)  [medium]
  07:50–08:00  Nail trim           (10 min)  [low]
──────────────────────────────────────────────────────────────
  Total scheduled : 60 min
  Owner budget    : 150 min
══════════════════════════════════════════════════════════════

  ✔  No scheduling conflicts.
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
python -m pytest tests/ -v

# Run with coverage:
pytest --cov
```

Sample test output:

```
==================================== test session starts ====================================
platform win32 -- Python 3.11.9, pytest-9.1.1
collected 21 items

tests/test_pawpal.py::TestTask::test_task_completion_changes_status PASSED
tests/test_pawpal.py::TestTask::test_task_reschedule_updates_time PASSED
tests/test_pawpal.py::TestTask::test_invalid_priority_raises PASSED
tests/test_pawpal.py::TestTask::test_invalid_duration_raises PASSED
tests/test_pawpal.py::TestTask::test_task_has_unique_id PASSED
tests/test_pawpal.py::TestPet::test_add_task_increases_count PASSED
tests/test_pawpal.py::TestPet::test_add_multiple_tasks PASSED
tests/test_pawpal.py::TestPet::test_remove_task_decreases_count PASSED
tests/test_pawpal.py::TestPet::test_remove_nonexistent_task_returns_false PASSED
tests/test_pawpal.py::TestPet::test_get_pending_tasks_excludes_completed PASSED
tests/test_pawpal.py::TestOwner::test_add_pet_increases_count PASSED
tests/test_pawpal.py::TestOwner::test_remove_pet PASSED
tests/test_pawpal.py::TestOwner::test_remove_nonexistent_pet_returns_false PASSED
tests/test_pawpal.py::TestScheduler::test_schedule_respects_priority_order PASSED
tests/test_pawpal.py::TestScheduler::test_schedule_does_not_exceed_budget PASSED
tests/test_pawpal.py::TestScheduler::test_no_conflicts_in_generated_schedule PASSED
tests/test_pawpal.py::TestScheduler::test_completed_tasks_excluded_from_schedule PASSED
tests/test_pawpal.py::TestScheduler::test_empty_task_list_gives_empty_schedule PASSED
tests/test_pawpal.py::TestScheduler::test_task_too_long_for_budget_is_skipped PASSED
tests/test_pawpal.py::TestScheduler::test_conflict_detection_finds_overlap PASSED
tests/test_pawpal.py::TestScheduler::test_explain_plan_contains_pet_name PASSED

==================================== 21 passed in 0.06s =====================================
```

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_tasks_by_priority()` | high → medium → low; ties broken by duration (shorter first) |
| Filtering | `Scheduler.filter_by_available_time()` | Greedy cut: stop adding tasks once owner's daily budget is reached |
| Conflict handling | `Scheduler.detect_conflicts()` | O(n²) pairwise overlap check; `build_schedule()` is always conflict-free by construction |
| Recurring tasks | `Task.is_recurring` + `recurrence_frequency` | Flagged with 🔁 in output; `get_recurring_tasks()` returns them for review |

## 📸 Demo Walkthrough

1. Run `python main.py` in the project root (with the venv activated).
2. The script creates owner **Jordan** with two pets: **Mochi** (Shiba Inu) and **Luna** (Scottish Fold).
3. Each pet has 6–7 tasks spanning high/medium/low priorities and recurring/one-off types.
4. The `Scheduler` sorts tasks by priority, filters to fit within Jordan's 150-minute daily budget, assigns back-to-back time slots starting at 07:00, and prints a formatted plan.
5. A conflict check runs automatically — the greedy algorithm guarantees no overlaps, which is confirmed with ✔.
