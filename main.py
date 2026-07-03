"""
main.py — PawPal+ CLI Demo Script

Run:  python main.py

Demonstrates:
  1. Standard priority-sorted schedule for two pets
  2. sort_by_time()  — tasks added out of order, re-sorted by scheduled_time
  3. filter_tasks()  — filter by category, priority, completion status
  4. mark_task_complete() — auto-spawns next occurrence for recurring tasks
  5. conflict_warnings()  — detects overlapping manually-built blocks
"""

from datetime import datetime, timedelta

from pawpal_system import Owner, Pet, Scheduler, ScheduledBlock, Task

# ── ANSI colour helpers ───────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
DIM    = "\033[2m"

PRIORITY_COLOUR = {"high": RED, "medium": YELLOW, "low": GREEN}

SEP  = f"{BOLD}{CYAN}{'═' * 62}{RESET}"
DASH = f"{BOLD}{CYAN}{'─' * 62}{RESET}"

def section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(SEP)

def print_schedule(scheduler: Scheduler) -> None:
    """Pretty-print a Scheduler's built plan."""
    pet, owner, blocks = scheduler.pet, scheduler.owner, scheduler.schedule
    print(f"\n{BOLD}  🐾  {pet.name} ({pet.species})  |  budget: {owner.available_minutes_per_day} min{RESET}")
    print(DASH)
    if not blocks:
        print(f"  {YELLOW}No tasks scheduled.{RESET}")
    else:
        for b in blocks:
            pc    = PRIORITY_COLOUR.get(b.task.priority, RESET)
            recur = " 🔁" if b.task.is_recurring else ""
            print(
                f"  {b.start_time.strftime('%H:%M')}–{b.end_time.strftime('%H:%M')}  "
                f"{BOLD}{b.task.title}{recur}{RESET}  "
                f"({b.task.duration_minutes} min)  [{pc}{b.task.priority}{RESET}]"
            )
            print(f"  {DIM}  → {b.reason}{RESET}")
    total = sum(b.duration() for b in blocks)
    skipped = [t for t in pet.get_pending_tasks() if t not in [b.task for b in blocks]]
    print(DASH)
    print(f"  Total: {total} min  |  Skipped: {len(skipped)} task(s)")
    print()

def print_task_list(tasks: list, label: str = "") -> None:
    """Print a flat list of Task objects."""
    if label:
        print(f"  {BOLD}{label}{RESET}")
    if not tasks:
        print(f"  {DIM}  (none){RESET}")
        return
    for t in tasks:
        st = t.scheduled_time.strftime("%H:%M") if t.scheduled_time else "—"
        done = "✅" if t.is_completed else "⏳"
        print(f"  {done} [{st}]  {t.title}  ({t.duration_minutes} min)  [{t.priority}]  cat={t.category}")


# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # ── Owner + pets ──────────────────────────────────────────────────────────
    jordan = Owner(name="Jordan", email="jordan@example.com", available_minutes_per_day=150)

    mochi = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3)
    mochi.add_task(Task("Morning walk",  "walk",       30, "high",   is_recurring=True,  recurrence_frequency="daily"))
    mochi.add_task(Task("Breakfast",     "feeding",    10, "high",   is_recurring=True,  recurrence_frequency="daily"))
    mochi.add_task(Task("Heartworm med", "medication",  5, "high",   is_recurring=True,  recurrence_frequency="daily"))
    mochi.add_task(Task("Fetch session", "enrichment", 20, "medium"))
    mochi.add_task(Task("Brush coat",    "grooming",   15, "low"))
    mochi.add_task(Task("Evening walk",  "walk",       30, "high",   is_recurring=True,  recurrence_frequency="daily"))
    mochi.add_task(Task("Dinner",        "feeding",    10, "high",   is_recurring=True,  recurrence_frequency="daily"))
    jordan.add_pet(mochi)

    luna = Pet(name="Luna", species="cat", breed="Scottish Fold", age_years=5)
    luna.add_task(Task("Morning feeding", "feeding",    10, "high",   is_recurring=True,  recurrence_frequency="daily"))
    luna.add_task(Task("Litter box",      "other",       5, "high",   is_recurring=True,  recurrence_frequency="daily"))
    luna.add_task(Task("Flea treatment",  "medication", 10, "medium", is_recurring=True,  recurrence_frequency="weekly"))
    luna.add_task(Task("Laser play",      "enrichment", 15, "medium"))
    luna.add_task(Task("Nail trim",       "grooming",   10, "low"))
    luna.add_task(Task("Evening feeding", "feeding",    10, "high",   is_recurring=True,  recurrence_frequency="daily"))
    jordan.add_pet(luna)

    print(f"\n{BOLD}PawPal+ — CLI Demo  {DIM}({today.strftime('%A, %B %d %Y')}){RESET}")

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Standard priority-sorted schedule
    # ─────────────────────────────────────────────────────────────────────────
    section("1 · Priority-sorted daily schedule")
    for pet in jordan.get_pets():
        sched = Scheduler(owner=jordan, pet=pet, day_start_hour=7, day_end_hour=21)
        sched.build_schedule(reference_date=today)
        print_schedule(sched)
        for w in sched.conflict_warnings():
            print(f"  {RED}{w}{RESET}")
        if not sched.conflict_warnings():
            print(f"  {GREEN}✔  No scheduling conflicts.{RESET}\n")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. sort_by_time() — tasks added intentionally out of order
    # ─────────────────────────────────────────────────────────────────────────
    section("2 · sort_by_time() — tasks added out of order")
    temp_pet = Pet(name="Test Pet", species="dog")
    # Add in reverse chronological order
    temp_pet.add_task(Task("Late task",    "other", 10, "low",    scheduled_time=today.replace(hour=18)))
    temp_pet.add_task(Task("No-time task", "other", 10, "medium"))  # no scheduled_time
    temp_pet.add_task(Task("Early task",   "other", 10, "high",   scheduled_time=today.replace(hour=8)))
    temp_pet.add_task(Task("Midday task",  "other", 10, "medium", scheduled_time=today.replace(hour=12)))

    temp_sched = Scheduler(owner=jordan, pet=temp_pet)
    sorted_tasks = temp_sched.sort_by_time()
    print_task_list(sorted_tasks, "After sort_by_time() — earliest first, no-time tasks last:")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. filter_tasks() — by category, priority, completion status
    # ─────────────────────────────────────────────────────────────────────────
    section("3 · filter_tasks() — various filters on Mochi's tasks")
    mochi_sched = Scheduler(owner=jordan, pet=mochi)
    all_tasks = mochi.get_tasks()

    walks = Scheduler.filter_tasks(all_tasks, category="walk")
    print_task_list(walks, "category='walk':")

    high_tasks = Scheduler.filter_tasks(all_tasks, priority="high")
    print_task_list(high_tasks, "priority='high':")

    # Mark one task complete to make the completion filter interesting
    mochi.get_tasks()[0].complete()
    done  = Scheduler.filter_tasks(all_tasks, completed=True)
    pending = Scheduler.filter_tasks(all_tasks, completed=False)
    print_task_list(done,    "completed=True:")
    print_task_list(pending, "completed=False (pending):")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. mark_task_complete() — auto-spawns next occurrence
    # ─────────────────────────────────────────────────────────────────────────
    section("4 · mark_task_complete() — recurring task auto-renewal")
    # Find a recurring task on Luna that isn't yet complete
    recurring = [t for t in luna.get_pending_tasks() if t.is_recurring][0]
    print(f"  Completing recurring task: '{recurring.title}' "
          f"(freq={recurring.recurrence_frequency})")

    luna_sched = Scheduler(owner=jordan, pet=luna)
    next_task  = luna_sched.mark_task_complete(recurring)

    if next_task:
        nxt_time = next_task.scheduled_time.strftime('%Y-%m-%d %H:%M') if next_task.scheduled_time else "—"
        print(f"  {GREEN}✔  Original task marked complete.{RESET}")
        print(f"  {GREEN}✔  Next occurrence auto-created: '{next_task.title}'  "
              f"@ {nxt_time}{RESET}")
    else:
        print(f"  {YELLOW}Task is not recurring — no next occurrence created.{RESET}")

    print(f"\n  Luna's task count after renewal: "
          f"{len(luna.get_tasks())} (was {len(luna.get_tasks()) - 1})")

    # ─────────────────────────────────────────────────────────────────────────
    # 5. conflict_warnings() — manually overlapping blocks
    # ─────────────────────────────────────────────────────────────────────────
    section("5 · conflict_warnings() — intentionally overlapping blocks")
    t_a = Task("Vet appointment", "vet",  60, "high")
    t_b = Task("Grooming session", "grooming", 45, "medium")
    # Both start at 10:00 — guaranteed overlap
    start = today.replace(hour=10)
    block_a = ScheduledBlock(task=t_a, start_time=start)
    block_b = ScheduledBlock(task=t_b, start_time=start + timedelta(minutes=30))

    conflict_sched = Scheduler(owner=jordan, pet=mochi)
    warnings = conflict_sched.conflict_warnings([block_a, block_b])

    if warnings:
        for w in warnings:
            print(f"  {RED}{w}{RESET}")
    else:
        print(f"  {GREEN}No conflicts found.{RESET}")

    # Same blocks with no overlap — just to confirm clean case
    block_c = ScheduledBlock(task=t_b, start_time=start + timedelta(minutes=61))
    clean_warnings = conflict_sched.conflict_warnings([block_a, block_c])
    if not clean_warnings:
        print(f"\n  {GREEN}✔  Adjusted blocks have no conflicts.{RESET}")

    print()


if __name__ == "__main__":
    main()
