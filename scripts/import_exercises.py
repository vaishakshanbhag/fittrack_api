"""One-time import: populate the ``exercises`` table from free-exercise-db.

This project has no migration framework (see ``scripts/migrate_add_users.py``),
so seeding reference data is its own one-off script rather than a fixture or
a route. Source: https://github.com/yuhonas/free-exercise-db (public domain),
pinned to a specific commit so re-running this script always imports the same
data, even if the upstream dataset changes later.

Also inserts one sentinel exercise, external_id="__unmatched__", used as the
fallback target by scripts/migrate_workouts_exercise_fk.py for legacy workout
rows whose free-text type/name can't be confidently matched to a real
exercise.

The script is idempotent: re-running it only inserts rows whose external_id
isn't already present.

Run from the project root:  ``uv run python scripts/import_exercises.py``
"""

import json
import sys
import urllib.request
from pathlib import Path

# Allow running as a plain script (``python scripts/import_exercises.py``) by
# putting the project root on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from db import Base, SessionLocal, engine  # noqa: E402
from models.db_models import Exercise  # noqa: E402

DATASET_COMMIT = "a859101d633a01c4a1a920d6a8ce41dabba0705f"
DATASET_URL = (
    f"https://raw.githubusercontent.com/yuhonas/free-exercise-db/{DATASET_COMMIT}"
    "/dist/exercises.json"
)

UNMATCHED_EXTERNAL_ID = "__unmatched__"
UNMATCHED_SENTINEL = {
    "id": UNMATCHED_EXTERNAL_ID,
    "name": "Unmatched Legacy Workout",
    "category": "unspecified",
    "level": "unspecified",
    "mechanic": None,
    "force": None,
    "equipment": None,
    "primaryMuscles": [],
    "secondaryMuscles": [],
    "instructions": [
        "Placeholder exercise assigned to legacy workouts whose original "
        "free-text type/name could not be confidently matched to a real "
        "catalog exercise during migration."
    ],
    "images": [],
}


def _fetch_dataset() -> list[dict]:
    """Download the aggregated exercise dataset as a list of dicts."""
    with urllib.request.urlopen(DATASET_URL) as response:
        data = json.load(response)
    data.append(UNMATCHED_SENTINEL)
    return data


def _to_exercise(entry: dict) -> Exercise:
    return Exercise(
        external_id=entry["id"],
        name=entry["name"],
        category=entry["category"],
        level=entry["level"],
        mechanic=entry.get("mechanic"),
        force=entry.get("force"),
        equipment=entry.get("equipment"),
        primary_muscles=entry.get("primaryMuscles", []),
        secondary_muscles=entry.get("secondaryMuscles", []),
        instructions=entry.get("instructions", []),
        images=entry.get("images", []),
    )


def main() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        existing_ids = set(db.scalars(select(Exercise.external_id)).all())

        dataset = _fetch_dataset()
        new_rows = [_to_exercise(e) for e in dataset if e["id"] not in existing_ids]

        if not new_rows:
            print(f"No new exercises to import ({len(existing_ids)} already present).")
            return

        db.add_all(new_rows)
        db.commit()
        print(
            f"Imported {len(new_rows)} new exercise(s) "
            f"({len(existing_ids)} already present, {len(dataset)} in dataset)."
        )


if __name__ == "__main__":
    main()
