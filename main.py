"""
main.py — PawPal+ CLI Demo Script

Run:  python main.py

This script exercises the full backend without the Streamlit UI.
It creates an owner with two pets, assigns tasks, generates schedules,
and prints a formatted daily plan to the terminal.
"""

from datetime import datetime

from pawpal_system import Owner, Pet, Scheduler, Task


# ── ANSI colours for nicer terminal output ────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
DIM    = "\033[2m"

PRIORITY_COLOUR = {"high": RED, "medium": YELLOW, "low": GREEN}


def print_schedule(scheduler: Scheduler) -> None:
    """Pretty-print a Scheduler's plan to stdout."""
    pet = scheduler.pet
    owner = scheduler.owner
    blocks = scheduler.schedule

    print(f"\n{BOLD}{CYAN}{'═' * 62}{RESET}")
    print(f"{BOLD}{CYAN}  🐾  Daily Plan for {pet.name} ({pet.species}){RESET}")
    print(f"{DIM}  Owner: {owner.name}  |  Budget: {owner.available_minutes_per_day} min{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 62}{RESET}")

    if not blocks:
        print(f"  {YELLOW}No tasks scheduled — check pet tasks and owner budget.{RESET}")
    else:
        for block in blocks:
            pc = PRIORITY_COLOUR.get(block.task.priority, RESET)
            recur = " 🔁" if block.task.is_recurring else ""
            print(
                f"  {block.start_time.strftime('%H:%M')}–{block.end_time.strftime('%H:%M')}  "
                f"{BOLD}{block.task.title}{recur}{RESET}  "
                f"({block.task.duration_minutes} min)  "
                f"[{pc}{block.task.priority}{RESET}]"
            )
            print(f"  {DIM}  → {block.reason}{RESET}")

    total = sum(b.duration() for b in blocks)
    skipped = [
        t for t in pet.get_pending_tasks()
        if t not in [b.task for b in blocks]
    ]

    print(f"{BOLD}{CYAN}{'─' * 62}{RESET}")
    print(f"  Total scheduled : {total} min")
    print(f"  Owner budget    : {owner.available_minutes_per_day} min")
    if skipped:
        print(f"  {YELLOW}Skipped ({len(skipped)} tasks — over time budget):{RESET}")
        for t in skipped:
            print(f"    • {t.title} [{t.priority}] {t.duration_minutes} min")
    print(f"{BOLD}{CYAN}{'═' * 62}{RESET}\n")


def main() -> None:
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # ── Owner ─────────────────────────────────────────────────────────────────
    jordan = Owner(name="Jordan", email="jordan@example.com", available_minutes_per_day=150)

    # ── Pet 1: Mochi the dog ──────────────────────────────────────────────────
    mochi = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3)

    mochi.add_task(Task("Morning walk",   "walk",       30, "high",   is_recurring=True,  recurrence_frequency="daily"))
    mochi.add_task(Task("Breakfast",      "feeding",    10, "high",   is_recurring=True,  recurrence_frequency="daily"))
    mochi.add_task(Task("Heartworm med",  "medication",  5, "high",   is_recurring=True,  recurrence_frequency="daily"))
    mochi.add_task(Task("Fetch session",  "enrichment", 20, "medium"))
    mochi.add_task(Task("Brush coat",     "grooming",   15, "low"))
    mochi.add_task(Task("Evening walk",   "walk",       30, "high",   is_recurring=True,  recurrence_frequency="daily"))
    mochi.add_task(Task("Dinner",         "feeding",    10, "high",   is_recurring=True,  recurrence_frequency="daily"))

    jordan.add_pet(mochi)

    # ── Pet 2: Luna the cat ───────────────────────────────────────────────────
    luna = Pet(name="Luna", species="cat", breed="Scottish Fold", age_years=5)

    luna.add_task(Task("Morning feeding", "feeding",    10, "high",   is_recurring=True,  recurrence_frequency="daily"))
    luna.add_task(Task("Litter box",      "other",       5, "high",   is_recurring=True,  recurrence_frequency="daily"))
    luna.add_task(Task("Flea treatment",  "medication", 10, "medium", is_recurring=True,  recurrence_frequency="weekly"))
    luna.add_task(Task("Laser play",      "enrichment", 15, "medium"))
    luna.add_task(Task("Nail trim",       "grooming",   10, "low"))
    luna.add_task(Task("Evening feeding", "feeding",    10, "high",   is_recurring=True,  recurrence_frequency="daily"))

    jordan.add_pet(luna)

    # ── Build & print schedules ───────────────────────────────────────────────
    print(f"\n{BOLD}PawPal+ — CLI Demo{RESET}  {DIM}({today.strftime('%A, %B %d %Y')}){RESET}")

    for pet in jordan.get_pets():
        sched = Scheduler(owner=jordan, pet=pet, day_start_hour=7, day_end_hour=21)
        sched.build_schedule(reference_date=today)
        print_schedule(sched)

        # Conflict check
        conflicts = sched.detect_conflicts()
        if conflicts:
            print(f"  {RED}⚠  Conflicts detected:{RESET}")
            for a, b in conflicts:
                print(f"    {a.task.title} ↔ {b.task.title}")
        else:
            print(f"  {GREEN}✔  No scheduling conflicts.{RESET}\n")


if __name__ == "__main__":
    main()
