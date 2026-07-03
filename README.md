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
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### Run the Streamlit app

```bash
# Windows
.venv\Scripts\streamlit.exe run app.py --server.port 8080

# macOS/Linux
streamlit run app.py
```

### Run the CLI demo

```bash
python main.py
```

### Run the test suite

```bash
python -m pytest tests/ -v
```

### 💾 Data Persistence

Owner profiles, pets, and tasks are automatically saved to `pawpal_data.json`
in the project root every time you make a change in the Streamlit UI.
When you reopen the app, your data is restored automatically — no manual
import needed.

To start fresh, click **Reset profile** in the sidebar (this deletes the
save file) or delete `pawpal_data.json` manually.

**Files involved:**
- `persistence.py` — `save_owner()` / `load_owner()` serialise/deserialise
  the full Owner → Pet → Task object graph to JSON
- `app.py` — calls `_save()` after every mutation; calls `load_owner()` at
  startup

### 🎨 Output Formatting

The CLI demo (`main.py`) uses ANSI colour codes and Unicode emoji for
structured, readable output:

| Element | Format |
|---|---|
| Section headers | ANSI bold cyan `══` borders |
| Priority labels | 🔴 high / 🟡 medium / 🟢 low |
| Recurring tasks | 🔁 badge |
| Conflict warnings | ANSI red ⚠ |
| Success messages | ANSI green ✔ |
| Scheduling reasons | ANSI dim indented text |

The Streamlit UI uses `st.success`, `st.warning`, `st.error`, progress bars,
and `st.dataframe` for the same information in a browser context.

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

**What the tests cover:**

| Group | Tests | What's verified |
|---|---|---|
| `TestTask` | 5 | Completion status, reschedule, invalid inputs, unique IDs |
| `TestPet` | 5 | Add/remove tasks, pending-only filter |
| `TestOwner` | 3 | Add/remove pets |
| `TestScheduler` | 8 | Priority order, budget cap, no conflicts, skip completed, empty list, over-budget task, conflict detection, explain_plan |
| `TestSortByTime` | 2 | Chronological order, None-time tasks sort last |
| `TestFilterTasks` | 5 | Filter by category, priority, completion, combined AND criteria |
| `TestRecurringTaskRenewal` | 5 | next_occurrence() daily/weekly/None, mark_task_complete() adds new task |
| `TestConflictWarnings` | 3 | Overlap detected, sequential blocks clear, return type is str |
| `TestEdgeCases` | 19 | All-completed → empty; budget = exact total; 1-min over window skipped; short-first tiebreak; medium before low; chronological blocks; explain_plan before build; start-time accuracy; property inheritance; new ID on recurrence; completed removed from pending; 3-way conflict count; adjacent blocks don't conflict; empty/no-criteria/zero-match filter; all-None sort; single-task sort |

**Confidence level: ★★★★★** (5/5)

Sample test output:

```
==================================== test session starts ====================================
platform win32 -- Python 3.11.9, pytest-9.1.1
collected 55 items

tests/test_pawpal.py::TestTask::test_task_completion_changes_status PASSED           [  1%]
tests/test_pawpal.py::TestTask::test_task_reschedule_updates_time PASSED             [  3%]
...
tests/test_pawpal.py::TestEdgeCases::test_sort_by_time_single_task PASSED            [100%]

==================================== 55 passed in 0.20s =====================================
```

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Priority sorting | `Scheduler.sort_tasks_by_priority()` | high → medium → low; ties broken by duration (shorter first — quick-wins heuristic) |
| Time-based sorting | `Scheduler.sort_by_time()` | Sorts by `Task.scheduled_time` ascending; tasks with no time slot are placed last via `(is None, value)` lambda key |
| Multi-criteria filtering | `Scheduler.filter_tasks()` | Static method; filters by `completed`, `category`, `priority`, or `pet_name` — criteria are AND-combined |
| Budget filtering | `Scheduler.filter_by_available_time()` | Greedy cut — stops adding tasks once `owner.available_minutes_per_day` is reached |
| Conflict detection | `Scheduler.detect_conflicts()` | O(n²) pairwise overlap check on `ScheduledBlock` objects; returns conflicting pairs |
| Conflict warnings | `Scheduler.conflict_warnings()` | Wraps `detect_conflicts()` and returns human-readable warning strings instead of raising exceptions |
| Recurring task renewal | `Task.next_occurrence()` + `Scheduler.mark_task_complete()` | Completing a recurring task auto-creates a new `Task` instance offset by `timedelta(days=1)` (daily) or `timedelta(weeks=1)` (weekly) and attaches it to the pet |

## ✨ Features

| Feature | Where | How it works |
|---|---|---|
| Owner profile | Sidebar | Creates an `Owner` with name and daily time budget (minutes) |
| Multi-pet support | Sidebar | Add/remove any number of `Pet` objects per owner |
| Task management | Per-pet tab | Add tasks with title, category, duration, priority, recurrence |
| Priority-based scheduling | Schedule tab | `Scheduler.sort_tasks_by_priority()` — high → medium → low; ties broken by duration |
| Time-based sorting | Per-pet tab filter | `Scheduler.sort_by_time()` — reorders task list by `scheduled_time` ascending |
| Multi-criteria filtering | Per-pet tab filter | `Scheduler.filter_tasks()` — filter by category, priority, and/or completion status |
| Budget enforcement | Schedule tab | `Scheduler.filter_by_available_time()` — greedy cut when owner budget is reached |
| Conflict detection | Schedule tab | `Scheduler.conflict_warnings()` — prominent error banner for overlapping blocks |
| Recurring task renewal | Per-pet tab ✔ button | `Scheduler.mark_task_complete()` — completing a recurring task auto-adds the next occurrence |
| Plan explanation | Schedule tab expandable | `Scheduler.explain_plan()` — plain-English reason for every scheduled block |
| Skipped task callout | Schedule tab | Warning cards for tasks that didn't fit the budget |

## 📸 Demo Walkthrough

### Workflow: Add a pet → add tasks → generate schedule

**Step 1 — Create owner profile**
Open the sidebar. Enter your name and set your daily care budget (e.g. 120 minutes). Click **Create profile**. The sidebar updates to show your name and budget.

**Step 2 — Add a pet**
Still in the sidebar, fill in your pet's name, species, breed, and age. Click **Add pet**. The pet appears in the sidebar list and a new tab opens in the main area.

**Step 3 — Add tasks to the pet**
Click the pet's tab. Expand **Add a new task**. Add several tasks with different priorities (e.g. Medication — high, 5 min; Morning walk — high, 30 min; Grooming — low, 15 min). Recurring tasks get a 🔁 badge.

**Step 4 — Filter and sort the task list**
Use the **Filter & Sort** row above the task list. Selecting `priority = high` instantly filters to only high-priority tasks via `Scheduler.filter_tasks()`. Checking **Sort by scheduled time** re-orders via `Scheduler.sort_by_time()`.

**Step 5 — Mark a recurring task complete**
Click ✔ on a recurring task. A toast notification confirms completion and announces the next occurrence was auto-created. The task list updates; the new instance appears as pending.

**Step 6 — Generate the daily schedule**
Click the **📅 Daily Schedule** tab. Choose a date and day window. Click **Generate schedule for all pets**. Each pet's schedule appears as:
- A budget progress bar (e.g. 80 / 120 min used)
- A table with time slots, task names, categories, priorities, and scheduling reasons
- A ✔ success banner (or ⚠️ conflict warning if blocks overlap)
- An expandable plain-English explanation from `explain_plan()`
- Warning cards for any tasks skipped due to budget

**Step 7 — CLI demo (no browser needed)**
```bash
python main.py
```

Sample output:
```
PawPal+ — CLI Demo  (Friday, July 03 2026)

══════════════════════════════════════════════════════════════
  🐾  Mochi (dog)  |  budget: 150 min
──────────────────────────────────────────────────────────────
  07:00–07:05  Heartworm med 🔁  (5 min)   [high]
    → High priority — scheduled first.
  07:05–07:15  Breakfast 🔁      (10 min)  [high]
    → High priority — scheduled first.
  07:25–07:55  Morning walk 🔁   (30 min)  [high]
    → High priority — scheduled first.
  08:25–08:45  Fetch session     (20 min)  [medium]
    → Medium/low priority task — fits within available time.
──────────────────────────────────────────────────────────────
  Total: 120 min  |  Skipped: 0 task(s)
  ✔  No scheduling conflicts.
```
