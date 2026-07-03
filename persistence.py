"""
persistence.py — JSON save/load for PawPal+

Serialises the entire Owner graph (owner → pets → tasks) to a single JSON
file and deserialises it back into live Python objects.

Usage:
    from persistence import save_owner, load_owner

    save_owner(jordan, "pawpal_data.json")
    jordan = load_owner("pawpal_data.json")
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

from pawpal_system import Owner, Pet, Task


# ── Date helpers ──────────────────────────────────────────────────────────────
_DT_FMT = "%Y-%m-%dT%H:%M:%S"


def _dt_to_str(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime(_DT_FMT) if dt else None


def _str_to_dt(s: Optional[str]) -> Optional[datetime]:
    return datetime.strptime(s, _DT_FMT) if s else None


# ── Serialise ─────────────────────────────────────────────────────────────────

def _task_to_dict(task: Task) -> dict:
    """Convert a Task dataclass to a JSON-serialisable dict."""
    return {
        "task_id":              task.task_id,
        "title":                task.title,
        "category":             task.category,
        "duration_minutes":     task.duration_minutes,
        "priority":             task.priority,
        "is_recurring":         task.is_recurring,
        "recurrence_frequency": task.recurrence_frequency,
        "is_completed":         task.is_completed,
        "scheduled_time":       _dt_to_str(task.scheduled_time),
    }


def _pet_to_dict(pet: Pet) -> dict:
    """Convert a Pet dataclass (and its tasks) to a JSON-serialisable dict."""
    return {
        "pet_id":    pet.pet_id,
        "name":      pet.name,
        "species":   pet.species,
        "breed":     pet.breed,
        "age_years": pet.age_years,
        "tasks":     [_task_to_dict(t) for t in pet.get_tasks()],
    }


def _owner_to_dict(owner: Owner) -> dict:
    """Convert an Owner (and all nested pets/tasks) to a JSON-serialisable dict."""
    return {
        "owner_id":                  owner.owner_id,
        "name":                      owner.name,
        "email":                     owner.email,
        "available_minutes_per_day": owner.available_minutes_per_day,
        "pets":                      [_pet_to_dict(p) for p in owner.get_pets()],
    }


# ── Deserialise ───────────────────────────────────────────────────────────────

def _dict_to_task(d: dict) -> Task:
    """Reconstruct a Task from its serialised dict, preserving the original task_id."""
    t = Task(
        title=d["title"],
        category=d.get("category", "other"),
        duration_minutes=d["duration_minutes"],
        priority=d["priority"],
        is_recurring=d.get("is_recurring", False),
        recurrence_frequency=d.get("recurrence_frequency", "none"),
        is_completed=d.get("is_completed", False),
        scheduled_time=_str_to_dt(d.get("scheduled_time")),
    )
    # Restore original ID so references remain stable
    object.__setattr__(t, "task_id", d["task_id"])
    return t


def _dict_to_pet(d: dict) -> Pet:
    """Reconstruct a Pet (and its tasks) from its serialised dict."""
    pet = Pet(
        name=d["name"],
        species=d.get("species", "other"),
        breed=d.get("breed", "unknown"),
        age_years=d.get("age_years", 1),
    )
    object.__setattr__(pet, "pet_id", d["pet_id"])
    for td in d.get("tasks", []):
        pet.add_task(_dict_to_task(td))
    return pet


def _dict_to_owner(d: dict) -> Owner:
    """Reconstruct an Owner (and all nested pets/tasks) from its serialised dict."""
    owner = Owner(
        name=d["name"],
        email=d.get("email", ""),
        available_minutes_per_day=d.get("available_minutes_per_day", 120),
    )
    object.__setattr__(owner, "owner_id", d["owner_id"])
    for pd in d.get("pets", []):
        owner.add_pet(_dict_to_pet(pd))
    return owner


# ── Public API ────────────────────────────────────────────────────────────────

def save_owner(owner: Owner, filepath: str = "pawpal_data.json") -> None:
    """
    Persist the owner graph to a JSON file.

    Args:
        owner:    The Owner object to serialise.
        filepath: Destination file path (created or overwritten).
    """
    data = _owner_to_dict(owner)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_owner(filepath: str = "pawpal_data.json") -> Optional[Owner]:
    """
    Load an Owner graph from a JSON file.

    Args:
        filepath: Source file path.

    Returns:
        Reconstructed Owner object, or None if the file does not exist.
    """
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _dict_to_owner(data)
