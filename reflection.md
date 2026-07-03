# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

The three core operations I identified for PawPal+ are:
1. **Add a pet** — an owner registers a pet with basic info (name, species, breed, age).
2. **Add/edit tasks** — attach care activities (walks, feeding, meds, etc.) to a pet with duration and priority.
3. **Generate a daily schedule** — the system sorts pending tasks by priority, fits them into the owner's available time window, and returns a conflict-free, time-stamped plan.

I designed five classes:

| Class | Responsibility |
|---|---|
| `Task` | A single care activity. Holds title, category, duration, priority, recurrence, and completion status. Implemented as a Python `dataclass` for brevity. |
| `Pet` | Represents one animal. Owns a list of `Task` objects and exposes `add_task`, `remove_task`, and `get_pending_tasks`. Also a `dataclass`. |
| `Owner` | The human user. Stores name, email, daily time budget (minutes), and a list of `Pet` objects. |
| `ScheduledBlock` | A wrapper that pairs a `Task` with a concrete `start_time` and a human-readable `reason`. Computed `end_time` via `@property`. |
| `Scheduler` | The algorithmic core. Takes an `Owner` and a `Pet`, sorts tasks by priority, filters by time budget, assigns consecutive time slots, detects conflicts, and explains the plan. |

Relationships: `Owner` owns `Pet`(s); `Pet` has `Task`(s); `Scheduler` references `Owner` and `Pet` and produces `ScheduledBlock`(s), each wrapping one `Task`.

**b. Design changes**

During skeleton creation, AI review flagged one missing element: the original sketch didn't have a dedicated `ScheduledBlock` class — tasks were going to be mutated directly with `scheduled_time`. I split that out into `ScheduledBlock` instead, because:

- It keeps `Task` immutable-ish (tasks don't need to know when they're scheduled).
- It makes conflict detection cleaner — blocks can be compared without touching the underlying task.
- It allows the same `Task` to appear in multiple schedules (e.g., across different days) without side effects.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers three constraints, applied in this order:

1. **Completion status** — `get_pending_tasks()` filters out any task already marked done before the scheduler sees it. There is no point scheduling work that's finished.
2. **Priority** — `sort_tasks_by_priority()` uses `sorted()` with a lambda key `(PRIORITY_ORDER[t.priority], t.duration_minutes)`. High-priority tasks always precede medium, which always precede low. Within the same priority, shorter tasks come first (quick-wins heuristic — minimises the number of tasks that get cut off at the end of the day).
3. **Owner time budget** — `filter_by_available_time()` greedily accumulates tasks until the running total would exceed `owner.available_minutes_per_day`. Any task that would push the total over the budget is skipped.

The priority constraint was ranked first because the scenario description explicitly mentions "priority" as the primary scheduling signal, and missing a high-priority task (medication, feeding) is more harmful than missing a low-priority one (grooming).

**b. Tradeoffs**

The scheduler uses a **greedy, priority-first** algorithm rather than an optimal knapsack-style search.

*Tradeoff:* A greedy approach can produce a suboptimal total-minutes-scheduled result. For example, if the budget is 30 minutes and we have tasks of [high/25 min, medium/20 min, low/10 min], the greedy algorithm picks the 25-minute high task and then the 10-minute low task (35 > 30, so medium is skipped even though 20+10=30 would also fit with more variety).

*Why it's reasonable here:* Pet care is priority-critical. A dog medication task at "high" should never be bumped in favour of fitting in more medium tasks. The predictability and simplicity of greedy also makes the scheduler's reasoning easy for users to understand — they can see exactly why each task was included or skipped.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
