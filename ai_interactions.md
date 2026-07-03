# AI Interactions Log — PawPal+

This document records significant AI-assisted decisions made during the
development of PawPal+, including agent workflows, prompt comparisons,
and manual corrections.

---

## Agent Workflow

### Phase 1 — UML and Class Skeleton

**Files modified:** `diagrams/uml.mmd`, `pawpal_system.py`

**Task requested of the agent:**
> "I am designing a pet care scheduling app with four classes: Owner, Pet,
> Task, and Scheduler. Owner owns multiple Pets; each Pet has a list of Tasks.
> Scheduler takes an Owner and builds a daily plan. Please generate a
> Mermaid.js class diagram with attributes and methods for each class, then
> convert it into Python dataclass skeletons."

**What the agent completed:**
- Generated a Mermaid class diagram with correct ownership arrows
  (`Owner → Pet`, `Pet → Task`, `Scheduler → ScheduledBlock → Task`)
- Produced Python dataclass stubs for `Task` and `Pet`, and a regular class
  skeleton for `Scheduler`
- Added `__post_init__` validation to `Task` (priority and duration checks)

**Manual corrections made:**
- The agent's initial UML did not include `ScheduledBlock` — tasks were going
  to mutate their own `scheduled_time`. I added `ScheduledBlock` as a
  separate wrapper class so that `Task` stays side-effect-free and the same
  task can be referenced across multiple days without data corruption.
- The agent placed all scheduling logic inside `Pet` (a `build_schedule()`
  method on the pet itself). I moved it to a dedicated `Scheduler` class to
  keep single-responsibility clean and make the algorithm independently
  testable.

---

### Phase 4 — Algorithm Layer

**Files modified:** `pawpal_system.py`, `main.py`

**Task requested of the agent:**
> "My PawPal+ scheduler currently sorts by priority and filters by available
> time. Suggest 3–4 additional lightweight algorithms that would make the
> scheduler more useful for a pet owner, and implement them in
> `pawpal_system.py`."

**What the agent completed:**
- `sort_by_time()` — sorts tasks by `scheduled_time` using a lambda that
  places `None` values last: `key=lambda t: (t.scheduled_time is None, t.scheduled_time or datetime.min)`
- `filter_tasks()` — static method with keyword-only arguments for
  `completed`, `category`, `priority`, `pet_name`; criteria are AND-combined
- `mark_task_complete()` — wraps `task.complete()` and calls
  `task.next_occurrence()` to auto-spawn the next recurrence
- `conflict_warnings()` — returns `list[str]` of human-readable warnings
  rather than raising exceptions

**Manual corrections made:**
- The agent also proposed a `weighted_priority_score()` method that assigned
  floating-point scores combining priority, urgency (days until due), and
  category importance. I evaluated it and decided **not** to include it
  because: (a) we don't track due dates in the current `Task` model, so
  urgency would always default to zero; (b) it introduced a tuning parameter
  (category weights) with no principled default. Including it would have
  been complexity without benefit. I documented this in `reflection.md §2b`.
- The agent's `filter_tasks` originally mutated the input list in-place. I
  changed it to return a new list to avoid unexpected side effects in the
  Streamlit rerun loop.

---

### Phase 5 — Test Suite Edge Cases

**Files modified:** `tests/test_pawpal.py`

**Task requested of the agent:**
> "For a priority-based greedy scheduler with recurring tasks and conflict
> detection, what are the most important boundary cases to test? List them
> with a one-line rationale for each."

**What the agent completed:**
Produced a checklist of 12 boundary scenarios. Highlights that were missing
from my existing suite:

| Suggested boundary | Why it matters |
|---|---|
| Budget exactly equals task total | Validates `<=` vs `<` in the greedy cut |
| Task ends 1 minute past day window | Validates `block_end > day_end` strictness |
| All tasks completed → empty schedule | Guards against showing stale data |
| Adjacent blocks share an endpoint but don't overlap | Validates `<` vs `<=` in `overlaps_with()` |
| 3 blocks all overlapping → 3 conflict pairs | Confirms O(n²) pair count is correct |
| `next_occurrence()` inherits all properties | Prevents silent attribute loss across recurrence |

**Manual corrections made:**
- The agent suggested testing `sort_by_time()` by checking that the output
  list equals a reference list constructed by hand. I changed this to check
  that `times == sorted(times)` instead — more robust because it doesn't
  depend on insertion order of the fixture tasks.
- One suggested test checked that `conflict_warnings()` raises a
  `ValueError` when passed an empty list. The actual implementation returns
  `[]`, not an exception. I verified the code, confirmed the agent was wrong,
  and wrote the test to match the real behaviour.

---

## AI Model / Prompting Strategy Comparison

Two distinct prompting strategies were compared during this project.

### Strategy A — Broad "implement this feature" prompt

**Tool:** Kiro agent mode  
**Prompt style:** *"Implement recurring task support in pawpal_system.py"*  
**Useful output:** The agent identified that three things needed to change —
`Task` needed a `next_occurrence()` method, `Scheduler` needed a
`mark_task_complete()` wrapper, and `main.py` needed a demo section. It
handled all three files in one pass.  
**Problems:** The agent added a `last_completed_date` attribute to `Task` that
wasn't in the UML and introduced a dependency on `date.today()` inside the
dataclass, making it harder to test deterministically (time-dependent).  
**Final decision:** Kept the multi-file coordination but removed
`last_completed_date`. Replaced `date.today()` with a `scheduled_time`
offset so tests can use fixed datetimes.

---

### Strategy B — Narrow "write this specific method" prompt

**Tool:** Kiro chat mode  
**Prompt style:** *"Write a Python method `sort_by_time(tasks: list[Task]) -> list[Task]`
that sorts by `Task.scheduled_time` ascending, placing tasks with `None`
scheduled_time last. Use a lambda key."*  
**Useful output:** Produced exactly the right lambda in one shot:
```python
key=lambda t: (t.scheduled_time is None, t.scheduled_time or datetime.min)
```
No extraneous code, no new dependencies.  
**Problems:** None — the narrow prompt gave a narrow, correct answer.  
**Final decision:** Adopted as-is. This strategy was consistently more
reliable for algorithmic helper methods where the interface was already
designed.

---

### Key takeaway from comparison

Broad prompts work well for **cross-file coordination** (figuring out what
needs to change and where), but they tend to introduce unasked-for complexity.
Narrow prompts work best for **single-method implementation** once the design
is already decided. The effective workflow was: use broad prompts to plan,
then narrow prompts to implement, then human review to cut anything that
wasn't explicitly requested.

---

## Persistence Layer — Agent Workflow

**Files modified:** `persistence.py`, `app.py`

**Task requested of the agent:**
> "Add JSON save/load persistence to PawPal+. The save function should
> serialise the entire Owner → Pet → Task graph. The load function should
> reconstruct live Python objects. Preserve original IDs so that references
> remain stable across restarts. Integrate auto-save into app.py at every
> mutation point."

**What the agent completed:**
- Created `persistence.py` with `save_owner()` / `load_owner()` and private
  serialise/deserialise helpers for each class
- Used `object.__setattr__()` to restore original `task_id`, `pet_id`,
  `owner_id` after reconstruction (dataclasses are frozen-ish but IDs need
  to match saved state)
- Added `load_owner()` call at session-state bootstrap in `app.py` so data
  is restored on page refresh
- Added `_save()` calls after every mutation (add/remove pet, add/remove
  task, mark complete)

**Manual corrections made:**
- The agent originally used `dataclasses.replace()` to clone objects during
  deserialisation. This didn't work for restoring IDs because `replace()`
  calls `__post_init__`, which regenerates the UUID. Switched to
  `object.__setattr__()` after verifying the dataclass is not frozen.
- Added `pawpal_data.json` to `.gitignore` so user-specific data files are
  not committed to the repository.
