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

AI was used across every phase, but the nature of its contribution shifted as the project matured:

- **Phase 1 (Design):** AI was most useful as a sounding board. I described the four core classes in plain language and asked it to produce a Mermaid.js class diagram. This surfaced a missing relationship (the original sketch didn't have `ScheduledBlock` — tasks were going to carry their own `scheduled_time` mutation). Having a visual representation immediately made the architecture clearer.

- **Phase 2–3 (Implementation + UI):** I used agent mode to generate class skeletons from the UML, then filled in logic incrementally. The most effective prompts were narrow and specific: *"Write `sort_tasks_by_priority` using a lambda key that sorts by priority then duration"* rather than *"implement the scheduler."* Broad prompts tended to produce bloated code with unnecessary abstractions.

- **Phase 4 (Algorithms):** Chat mode was useful for comparing approaches — e.g., asking whether a greedy or knapsack algorithm was more appropriate for daily pet care scheduling. The answer helped me articulate *why* I chose greedy (priority is non-negotiable in pet care; missing a medication task is worse than suboptimal total-minutes-packed).

- **Phase 5 (Testing):** Asking "what are the most important boundary cases for a priority-based scheduler?" generated a useful checklist. I used it to audit my own test coverage and found gaps: the 1-minute-over-window edge case and adjacent-blocks-don't-conflict were both prompted by AI review.

**b. Judgment and verification**

One concrete example: when asked to review the scheduler, the AI suggested replacing `filter_by_available_time()` with a proper 0/1 knapsack algorithm to maximise total minutes scheduled. The suggestion was technically correct — greedy can leave gaps when tasks have uneven sizes.

I kept the greedy approach for two reasons:

1. **Priority semantics matter more than packing efficiency.** A knapsack optimizer might demote a high-priority 45-minute medication task in favour of three 15-minute low-priority enrichment tasks that pack tighter. That's the wrong outcome for a pet-care application.
2. **Readability and debuggability.** The greedy loop is 8 lines and obvious. The knapsack DP table is ~30 lines of index arithmetic that a busy developer (or student grader) would struggle to audit quickly.

I documented this tradeoff explicitly in Section 2b.

---

## 4. Testing and Verification

**a. What you tested**

The test suite has 55 tests across 9 classes covering:

- **Normal paths** (`TestTask`, `TestPet`, `TestOwner`, `TestScheduler`): basic CRUD operations, status changes, and schedule generation under typical conditions.
- **Algorithm correctness** (`TestSortByTime`, `TestFilterTasks`, `TestRecurringTaskRenewal`, `TestConflictWarnings`): verifying that sorting, filtering, recurring-task renewal, and conflict detection all produce the expected output.
- **Boundary / edge cases** (`TestEdgeCases`): 19 tests targeting the boundaries that are most likely to break silently — exact budget equality, 1-minute window overflow, all-tasks-completed, same-priority tiebreaking, adjacent-but-not-overlapping blocks, empty inputs, and inherited properties on recurrence.

These tests matter because pet care has real stakes. Missing a medication task or double-booking two activities because of an off-by-one error in the time-window check could mislead a user. The edge cases were specifically chosen to probe the exact boundary conditions in the greedy algorithm and `timedelta` arithmetic.

**b. Confidence**

Confidence: ★★★★★ (5/5) for the logic covered by the test suite.

Edge cases I would test next with more time:
- **Multi-pet shared budget**: what happens if the same owner has 10 pets and 60-minute budget — does the scheduler per-pet or pool-wide?
- **Timezone-aware datetimes**: the current code uses naive `datetime` objects; adding `pytz`/`zoneinfo` support would require re-testing all time arithmetic.
- **Concurrent modification**: adding a task while a schedule is being built (not an issue in the synchronous CLI, but relevant in the async Streamlit context).
- **Very large task lists** (1000+ tasks): confirm `O(n²)` conflict detection stays within acceptable time bounds.

---

## 5. Reflection

**a. What went well**

The separation of concerns between `pawpal_system.py` and `app.py` worked extremely well. Because all scheduling logic lives in the backend module, the Streamlit UI is thin — it just calls methods and displays results. This made Phase 6 UI upgrades painless: swapping `task.complete()` for `scheduler.mark_task_complete()` and adding `conflict_warnings()` banners required only UI-layer changes, zero backend rewrites.

The test-driven mindset also paid off. Several edge cases (the 1-minute window overflow, the adjacent-blocks non-conflict) were caught by tests *before* they could surface as confusing UI bugs.

**b. What you would improve**

The owner budget is treated as a single flat pool shared across all pets. In a real household with two dogs and a cat, some tasks genuinely compete for the same time slot while others are independent. A next iteration would model per-pet time windows and distinguish between tasks that require active owner participation vs. passive supervision.

I would also add a proper date-persistence layer (even just JSON to disk) so that session state survives browser refresh. Currently, closing the Streamlit tab loses all data.

**c. Key takeaway**

The most important lesson was about the division of responsibility between human architect and AI code generator. AI is fast and accurate at producing *implementations* of well-specified interfaces — give it a clear method signature and docstring, and it will fill in the body reliably. What it cannot do well is decide *which* interfaces belong in the system in the first place, or adjudicate between competing design tradeoffs that involve non-technical constraints (like "a medication task must never be demoted by a packing optimizer").

The human architect's job is to own those decisions — to know *why* the system is structured the way it is, to push back on AI suggestions that are technically correct but contextually wrong, and to write tests that encode business rules rather than just coverage numbers. AI handles the "how"; the architect owns the "why."
