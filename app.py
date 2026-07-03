"""
app.py — PawPal+ Streamlit UI
Connects the Streamlit front-end to the pawpal_system.py backend logic.
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

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

# ── Session-state bootstrap ───────────────────────────────────────────────────
# Streamlit re-runs the entire script on every interaction.
# We store the Owner object in st.session_state so it persists across reruns.
if "owner" not in st.session_state:
    st.session_state.owner: Owner | None = None

if "schedule_results" not in st.session_state:
    st.session_state.schedule_results: dict = {}   # pet_id → list[ScheduledBlock]


# ── Helper ────────────────────────────────────────────────────────────────────
def get_owner() -> Owner | None:
    return st.session_state.owner


def priority_badge(priority: str) -> str:
    colours = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    return colours.get(priority, "⚪")


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
            submitted = st.form_submit_button("Create profile")
            if submitted and owner_name.strip():
                st.session_state.owner = Owner(
                    name=owner_name.strip(),
                    email=owner_email.strip(),
                    available_minutes_per_day=int(budget),
                )
                st.rerun()
    else:
        owner = get_owner()
        st.success(f"**{owner.name}**  |  Budget: {owner.available_minutes_per_day} min/day")
        if st.button("Reset profile", use_container_width=True):
            st.session_state.owner = None
            st.session_state.schedule_results = {}
            st.rerun()

    st.divider()

    # ── Add a pet ────────────────────────────────────────────────────────────
    if get_owner() is not None:
        st.subheader("🐶 Add a Pet")
        with st.form("add_pet_form"):
            pet_name    = st.text_input("Pet name", value="Mochi")
            species     = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
            breed       = st.text_input("Breed (optional)", value="")
            age         = st.number_input("Age (years)", min_value=0, max_value=30, value=2)
            add_pet_btn = st.form_submit_button("Add pet")

            if add_pet_btn and pet_name.strip():
                new_pet = Pet(
                    name=pet_name.strip(),
                    species=species,
                    breed=breed.strip() or "unknown",
                    age_years=int(age),
                )
                st.session_state.owner.add_pet(new_pet)
                st.rerun()

        # ── Pet list ─────────────────────────────────────────────────────────
        pets = get_owner().get_pets()
        if pets:
            st.divider()
            st.subheader("🐾 Your Pets")
            for pet in pets:
                n_tasks = len(pet.get_tasks())
                n_pending = len(pet.get_pending_tasks())
                with st.expander(f"{pet.name}  ({pet.species})", expanded=False):
                    st.write(f"Breed: {pet.breed}  |  Age: {pet.age_years} yr")
                    st.write(f"Tasks: {n_tasks} total, {n_pending} pending")
                    if st.button(f"Remove {pet.name}", key=f"del_pet_{pet.pet_id}"):
                        st.session_state.owner.remove_pet(pet.pet_id)
                        # Clear any cached schedule for this pet
                        st.session_state.schedule_results.pop(pet.pet_id, None)
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

pets = owner.get_pets()  # owner is guaranteed non-None past this point
if not pets:
    st.info("👈  Add at least one pet in the sidebar to manage tasks.")
    st.stop()

# ── Tabs: one per pet ─────────────────────────────────────────────────────────
tab_labels = [f"{p.name}" for p in pets] + ["📅 Daily Schedule"]
tabs = st.tabs(tab_labels)

# ─────────────────────────────────────────────────────────────────────────────
# Per-pet task management tabs
# ─────────────────────────────────────────────────────────────────────────────
for idx, pet in enumerate(pets):
    with tabs[idx]:
        st.subheader(f"Tasks for {pet.name}  ({pet.species}, {pet.age_years} yr)")

        # ── Add task form ──────────────────────────────────────────────────
        with st.expander("➕ Add a new task", expanded=True):
            with st.form(f"add_task_{pet.pet_id}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    t_title    = st.text_input("Task title", value="Morning walk")
                    t_category = st.selectbox("Category", sorted(TASK_CATEGORIES))
                with col2:
                    t_duration = st.number_input(
                        "Duration (minutes)", min_value=1, max_value=240, value=20
                    )
                    t_priority = st.selectbox("Priority", ["high", "medium", "low"], index=1)
                with col3:
                    t_recurring = st.checkbox("Recurring task?")
                    t_freq      = st.selectbox(
                        "Frequency",
                        [o for o in RECURRENCE_OPTIONS if o != "none"],
                        disabled=not t_recurring,
                    )

                add_task_btn = st.form_submit_button("Add task", use_container_width=True)
                if add_task_btn and t_title.strip():
                    new_task = Task(
                        title=t_title.strip(),
                        category=t_category,
                        duration_minutes=int(t_duration),
                        priority=t_priority,
                        is_recurring=t_recurring,
                        recurrence_frequency=t_freq if t_recurring else "none",
                    )
                    pet.add_task(new_task)
                    # Invalidate cached schedule when tasks change
                    st.session_state.schedule_results.pop(pet.pet_id, None)
                    st.success(f"Added **{new_task.title}** to {pet.name}'s tasks.")
                    st.rerun()

        # ── Task list ──────────────────────────────────────────────────────
        all_tasks = pet.get_tasks()
        if not all_tasks:
            st.info("No tasks yet. Add one above.")
        else:
            st.write(f"**{len(all_tasks)} task(s)** — {len(pet.get_pending_tasks())} pending")

            for task in all_tasks:
                col_a, col_b, col_c, col_d = st.columns([4, 2, 2, 1])
                status_icon = "✅" if task.is_completed else "⏳"
                recur_icon  = " 🔁" if task.is_recurring else ""

                col_a.markdown(
                    f"{status_icon} **{task.title}**{recur_icon}  "
                    f"`{task.category}`"
                )
                col_b.write(f"{task.duration_minutes} min")
                col_c.write(f"{priority_badge(task.priority)} {task.priority}")

                with col_d:
                    if not task.is_completed:
                        if st.button("✔", key=f"done_{task.task_id}", help="Mark complete"):
                            task.complete()
                            st.session_state.schedule_results.pop(pet.pet_id, None)
                            st.rerun()
                    else:
                        if st.button("🗑", key=f"del_{task.task_id}", help="Remove task"):
                            pet.remove_task(task.task_id)
                            st.session_state.schedule_results.pop(pet.pet_id, None)
                            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Daily Schedule tab
# ─────────────────────────────────────────────────────────────────────────────
with tabs[-1]:
    st.subheader("📅 Daily Schedule")
    st.caption(f"Owner: **{owner.name}**  |  Time budget: **{owner.available_minutes_per_day} min**")

    ref_date = st.date_input("Schedule date", value=datetime.today())
    ref_dt   = datetime.combine(ref_date, datetime.min.time())

    col_start, col_end = st.columns(2)
    day_start = col_start.number_input("Day starts (hour)", min_value=0, max_value=23, value=7)
    day_end   = col_end.number_input("Day ends (hour)",   min_value=1, max_value=24, value=21)

    if st.button("🗓️ Generate schedule for all pets", use_container_width=True, type="primary"):
        st.session_state.schedule_results = {}
        for pet in pets:
            scheduler = Scheduler(
                owner=owner,
                pet=pet,
                day_start_hour=int(day_start),
                day_end_hour=int(day_end),
            )
            blocks = scheduler.build_schedule(reference_date=ref_dt)
            st.session_state.schedule_results[pet.pet_id] = {
                "blocks":    blocks,
                "scheduler": scheduler,
            }

    # ── Display results ───────────────────────────────────────────────────
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
            conflicts = scheduler.detect_conflicts()

            st.markdown(f"### {pet.name}  `{pet.species}`")

            if not blocks:
                st.warning(f"No tasks scheduled for {pet.name} — all tasks may be complete or over budget.")
            else:
                total_mins = sum(b.duration() for b in blocks)

                # Progress bar — fraction of budget used
                fraction = min(total_mins / owner.available_minutes_per_day, 1.0)
                st.progress(fraction, text=f"{total_mins} / {owner.available_minutes_per_day} min used")

                # Schedule table
                rows = []
                for b in blocks:
                    rows.append({
                        "Time":     f"{b.start_time.strftime('%H:%M')} – {b.end_time.strftime('%H:%M')}",
                        "Task":     ("🔁 " if b.task.is_recurring else "") + b.task.title,
                        "Category": b.task.category,
                        "Duration": f"{b.task.duration_minutes} min",
                        "Priority": priority_badge(b.task.priority) + " " + b.task.priority,
                        "Reason":   b.reason,
                    })
                st.dataframe(rows, use_container_width=True, hide_index=True)

                # Conflict report
                if conflicts:
                    st.error(f"⚠️  {len(conflicts)} conflict(s) detected!")
                    for a, b_block in conflicts:
                        st.write(f"  • **{a.task.title}** overlaps with **{b_block.task.title}**")
                else:
                    st.success("✔ No scheduling conflicts.")

                # Skipped tasks
                scheduled_ids = {b.task.task_id for b in blocks}
                skipped = [t for t in pet.get_pending_tasks() if t.task_id not in scheduled_ids]
                if skipped:
                    with st.expander(f"⏭ Skipped tasks ({len(skipped)}) — over time budget"):
                        for t in skipped:
                            st.write(
                                f"- **{t.title}** [{t.priority}] {t.duration_minutes} min"
                            )

            st.divider()
