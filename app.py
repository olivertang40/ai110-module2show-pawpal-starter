"""
app.py — PawPal+ Streamlit UI  (Phase 6 — final)
Full integration of Scheduler algorithm layer into the UI.

New in Phase 6:
- Filter panel: filter task list by category, priority, or completion status
  using Scheduler.filter_tasks()
- sort_by_time toggle: reorder the task list by scheduled_time via
  Scheduler.sort_by_time()
- conflict_warnings() surface: warning banner replaces silent detection
- mark_task_complete() used for recurring task ✔ button — auto-spawns next
  occurrence and shows a confirmation toast
- Skipped-task callout redesigned as st.warning cards
- Schedule explanation: expandable plain-English reasoning from explain_plan()
- JSON persistence: owner + pets + tasks auto-saved to pawpal_data.json on
  every change, auto-loaded on startup
"""

import streamlit as st
from datetime import datetime

from pawpal_system import (
    Owner,
    Pet,
    Scheduler,
    Task,
    PRIORITY_ORDER,
    TASK_CATEGORIES,
    RECURRENCE_OPTIONS,
)
from persistence import save_owner, load_owner

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

# ── Session-state bootstrap ───────────────────────────────────────────────────
if "owner" not in st.session_state:
    # Try to restore from disk on first load
    st.session_state.owner: Owner | None = load_owner("pawpal_data.json")

if "schedule_results" not in st.session_state:
    st.session_state.schedule_results: dict = {}   # pet_id → {blocks, scheduler}


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_owner() -> Owner | None:
    return st.session_state.owner

def _save() -> None:
    """Persist current owner state to disk after any mutation."""
    if st.session_state.owner is not None:
        save_owner(st.session_state.owner, "pawpal_data.json")

def priority_badge(priority: str) -> str:
    return {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")

def priority_color(priority: str) -> str:
    return {"high": "#FF4B4B", "medium": "#FFA500", "low": "#21C354"}.get(priority, "#888")


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — Owner & Pet management
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("🐾 PawPal+")
    st.caption("Smart pet care scheduling")
    st.divider()

    # ── Owner setup ──────────────────────────────────────────────────────────
    st.subheader("👤 Owner Profile")

    if get_owner() is None:
        with st.form("owner_form"):
            owner_name  = st.text_input("Your name", value="Jordan")
            owner_email = st.text_input("Email (optional)", value="")
            budget      = st.number_input(
                "Daily care budget (minutes)", min_value=10, max_value=480, value=120, step=5
            )
            if st.form_submit_button("Create profile") and owner_name.strip():
                st.session_state.owner = Owner(
                    name=owner_name.strip(),
                    email=owner_email.strip(),
                    available_minutes_per_day=int(budget),
                )
                _save()
                st.rerun()
    else:
        owner = get_owner()
        st.success(f"**{owner.name}**  |  Budget: {owner.available_minutes_per_day} min/day")
        st.caption("💾 Data auto-saved to `pawpal_data.json`")
        if st.button("Reset profile", use_container_width=True):
            import os
            st.session_state.owner = None
            st.session_state.schedule_results = {}
            if os.path.exists("pawpal_data.json"):
                os.remove("pawpal_data.json")
            st.rerun()

    st.divider()

    # ── Add a pet ────────────────────────────────────────────────────────────
    if get_owner() is not None:
        st.subheader("🐶 Add a Pet")
        with st.form("add_pet_form"):
            pet_name = st.text_input("Pet name", value="Mochi")
            species  = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
            breed    = st.text_input("Breed (optional)", value="")
            age      = st.number_input("Age (years)", min_value=0, max_value=30, value=2)
            if st.form_submit_button("Add pet") and pet_name.strip():
                st.session_state.owner.add_pet(Pet(
                    name=pet_name.strip(),
                    species=species,
                    breed=breed.strip() or "unknown",
                    age_years=int(age),
                ))
                _save()
                st.rerun()

        pets = get_owner().get_pets()
        if pets:
            st.divider()
            st.subheader("🐾 Your Pets")
            for pet in pets:
                with st.expander(f"{pet.name}  ({pet.species})", expanded=False):
                    st.write(f"Breed: {pet.breed}  |  Age: {pet.age_years} yr")
                    n_pending = len(pet.get_pending_tasks())
                    st.write(f"Tasks: {len(pet.get_tasks())} total, {n_pending} pending")
                    if st.button(f"Remove {pet.name}", key=f"del_pet_{pet.pet_id}"):
                        st.session_state.owner.remove_pet(pet.pet_id)
                        st.session_state.schedule_results.pop(pet.pet_id, None)
                        _save()
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN AREA
# ═══════════════════════════════════════════════════════════════════════════════
st.title("🐾 PawPal+")
st.caption("Smart pet care scheduling — powered by Python OOP")

owner = get_owner()
if owner is None:
    st.info("👈  Create your owner profile in the sidebar to get started.")
    st.stop()

pets = owner.get_pets()
if not pets:
    st.info("👈  Add at least one pet in the sidebar to manage tasks.")
    st.stop()

# ── Tabs: one per pet + schedule ─────────────────────────────────────────────
tabs = st.tabs([p.name for p in pets] + ["📅 Daily Schedule"])


# ─────────────────────────────────────────────────────────────────────────────
# Per-pet task tabs
# ─────────────────────────────────────────────────────────────────────────────
for idx, pet in enumerate(pets):
    with tabs[idx]:
        st.subheader(f"Tasks for {pet.name}  ({pet.species}, {pet.age_years} yr)")

        # ── Add task form ─────────────────────────────────────────────────
        with st.expander("➕ Add a new task", expanded=False):
            with st.form(f"add_task_{pet.pet_id}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    t_title    = st.text_input("Task title", value="Morning walk")
                    t_category = st.selectbox("Category", sorted(TASK_CATEGORIES))
                with col2:
                    t_duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
                    t_priority = st.selectbox("Priority", ["high", "medium", "low"], index=1)
                with col3:
                    t_recurring = st.checkbox("Recurring task?")
                    t_freq = st.selectbox(
                        "Frequency",
                        [o for o in RECURRENCE_OPTIONS if o != "none"],
                        disabled=not t_recurring,
                    )
                if st.form_submit_button("Add task", use_container_width=True) and t_title.strip():
                    pet.add_task(Task(
                        title=t_title.strip(),
                        category=t_category,
                        duration_minutes=int(t_duration),
                        priority=t_priority,
                        is_recurring=t_recurring,
                        recurrence_frequency=t_freq if t_recurring else "none",
                    ))
                    st.session_state.schedule_results.pop(pet.pet_id, None)
                    _save()
                    st.rerun()

        # ── Algorithm controls: filter + sort ────────────────────────────
        st.markdown("**🔍 Filter & Sort**")
        fc1, fc2, fc3, fc4 = st.columns(4)
        f_cat      = fc1.selectbox("Category", ["all"] + sorted(TASK_CATEGORIES), key=f"fcat_{pet.pet_id}")
        f_pri      = fc2.selectbox("Priority",  ["all", "high", "medium", "low"],  key=f"fpri_{pet.pet_id}")
        f_status   = fc3.selectbox("Status",    ["all", "pending", "completed"],   key=f"fsta_{pet.pet_id}")
        sort_time  = fc4.checkbox("Sort by scheduled time", key=f"fsort_{pet.pet_id}")

        # Apply filters using Scheduler.filter_tasks()
        all_tasks = pet.get_tasks()
        filtered = Scheduler.filter_tasks(
            all_tasks,
            category   = None if f_cat    == "all" else f_cat,
            priority   = None if f_pri    == "all" else f_pri,
            completed  = None if f_status == "all" else (f_status == "completed"),
        )

        # Apply sort using Scheduler.sort_by_time()
        if sort_time:
            # Need a temporary scheduler just to call sort_by_time on the filtered list
            _tmp = Scheduler(owner=owner, pet=pet)
            filtered = _tmp.sort_by_time(filtered)

        # ── Task list ─────────────────────────────────────────────────────
        st.divider()
        if not all_tasks:
            st.info("No tasks yet. Use **Add a new task** above.")
        else:
            total  = len(all_tasks)
            shown  = len(filtered)
            pend   = len(pet.get_pending_tasks())
            st.caption(f"Showing {shown} of {total} tasks  |  {pend} pending")

            if not filtered:
                st.warning("No tasks match the current filters.")
            else:
                for task in filtered:
                    col_a, col_b, col_c, col_d, col_e = st.columns([4, 2, 2, 2, 1])
                    status_icon = "✅" if task.is_completed else "⏳"
                    recur_icon  = " 🔁" if task.is_recurring else ""
                    sched_time  = task.scheduled_time.strftime("%H:%M") if task.scheduled_time else "—"

                    col_a.markdown(
                        f"{status_icon} **{task.title}**{recur_icon}  `{task.category}`"
                    )
                    col_b.write(f"{task.duration_minutes} min")
                    col_c.write(f"{priority_badge(task.priority)} {task.priority}")
                    col_d.write(f"🕐 {sched_time}")

                    with col_e:
                        if not task.is_completed:
                            if st.button("✔", key=f"done_{task.task_id}", help="Mark complete"):
                                # Use mark_task_complete() to handle recurring renewal
                                tmp_sched = Scheduler(owner=owner, pet=pet)
                                next_t = tmp_sched.mark_task_complete(task)
                                st.session_state.schedule_results.pop(pet.pet_id, None)
                                _save()
                                if next_t:
                                    st.toast(
                                        f"✅ '{task.title}' done!  "
                                        f"Next occurrence added for "
                                        f"{next_t.scheduled_time.strftime('%b %d') if next_t.scheduled_time else 'tomorrow'}.",
                                        icon="🔁",
                                    )
                                st.rerun()
                        else:
                            if st.button("🗑", key=f"del_{task.task_id}", help="Remove task"):
                                pet.remove_task(task.task_id)
                                st.session_state.schedule_results.pop(pet.pet_id, None)
                                _save()
                                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Daily Schedule tab
# ─────────────────────────────────────────────────────────────────────────────
with tabs[-1]:
    st.subheader("📅 Daily Schedule")
    st.caption(f"Owner: **{owner.name}**  |  Time budget: **{owner.available_minutes_per_day} min**")

    col_date, col_start, col_end = st.columns(3)
    ref_date  = col_date.date_input("Schedule date", value=datetime.today())
    day_start = col_start.number_input("Day starts (hour)", min_value=0, max_value=23, value=7)
    day_end   = col_end.number_input("Day ends (hour)",   min_value=1, max_value=24, value=21)
    ref_dt    = datetime.combine(ref_date, datetime.min.time())

    if st.button("🗓️ Generate schedule for all pets", use_container_width=True, type="primary"):
        st.session_state.schedule_results = {}
        for pet in pets:
            sched = Scheduler(
                owner=owner, pet=pet,
                day_start_hour=int(day_start),
                day_end_hour=int(day_end),
            )
            sched.build_schedule(reference_date=ref_dt)
            st.session_state.schedule_results[pet.pet_id] = {"blocks": sched.schedule, "scheduler": sched}

    results = st.session_state.schedule_results
    if not results:
        st.info("Click **Generate schedule** above to build today's plan.")
    else:
        for pet in pets:
            data = results.get(pet.pet_id)
            if not data:
                continue

            blocks    = data["blocks"]
            scheduler = data["scheduler"]

            st.markdown(f"### {pet.name}  `{pet.species}`")

            if not blocks:
                st.warning(
                    f"No tasks scheduled for **{pet.name}** — "
                    "all tasks may be complete, or every task exceeds the remaining budget."
                )
            else:
                total_mins = sum(b.duration() for b in blocks)
                fraction   = min(total_mins / owner.available_minutes_per_day, 1.0)
                st.progress(fraction, text=f"{total_mins} / {owner.available_minutes_per_day} min used")

                # ── Conflict warnings (prominent banner) ──────────────────
                warnings = scheduler.conflict_warnings()
                if warnings:
                    for w in warnings:
                        st.error(f"⚠️ {w}")
                else:
                    st.success("✔ No scheduling conflicts detected.")

                # ── Schedule table ────────────────────────────────────────
                rows = []
                for b in blocks:
                    rows.append({
                        "Time":      f"{b.start_time.strftime('%H:%M')} – {b.end_time.strftime('%H:%M')}",
                        "Task":      ("🔁 " if b.task.is_recurring else "") + b.task.title,
                        "Category":  b.task.category,
                        "Duration":  f"{b.task.duration_minutes} min",
                        "Priority":  priority_badge(b.task.priority) + " " + b.task.priority,
                        "Why scheduled": b.reason,
                    })
                st.dataframe(rows, use_container_width=True, hide_index=True)

                # ── Plain-English plan explanation ────────────────────────
                with st.expander("📋 Full plan explanation"):
                    st.code(scheduler.explain_plan(), language=None)

                # ── Skipped tasks ─────────────────────────────────────────
                scheduled_ids = {b.task.task_id for b in blocks}
                skipped = [t for t in pet.get_pending_tasks() if t.task_id not in scheduled_ids]
                if skipped:
                    with st.expander(f"⏭ Skipped tasks ({len(skipped)}) — didn't fit in budget"):
                        for t in skipped:
                            st.warning(
                                f"**{t.title}** — {priority_badge(t.priority)} {t.priority} "
                                f"| {t.duration_minutes} min "
                                f"| category: {t.category}",
                                icon="⏭",
                            )

            st.divider()
