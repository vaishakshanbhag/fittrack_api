"""One-off migration: add the ``users`` table and a NOT NULL ``workouts.user_id``.

This project has no migration framework (schema is otherwise managed by
``Base.metadata.create_all`` on startup, which only *creates missing* tables and
never alters existing ones). Adding a NOT NULL foreign key to a ``workouts``
table that already contains rows therefore needs an explicit, one-time step.

Strategy (chosen with the maintainer): preserve existing data by backfilling.
    1. Create the ``users`` table.
    2. Ensure a placeholder "legacy" user exists to own pre-migration workouts.
       It has an unusable password hash ("!") that can never match a real
       password, so nobody can authenticate as it.
    3. Rebuild ``workouts`` with the new NOT NULL ``user_id`` column (SQLite
       cannot add a NOT NULL FK in place), copying every existing row and
       assigning it to the legacy user.

The script is idempotent: re-running it is a no-op once ``user_id`` exists.

Run from the project root:  ``uv run python scripts/migrate_add_users.py``
"""

import sys
from pathlib import Path

# Allow running as a plain script (``python scripts/migrate_add_users.py``) by
# putting the project root on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, text  # noqa: E402

from db import Base, SessionLocal, engine  # noqa: E402
from models.db_models import User, Workout  # noqa: E402

LEGACY_USER_EMAIL = "legacy@fittrack.local"
UNUSABLE_PASSWORD_HASH = "!"


def _workouts_already_migrated() -> bool:
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(workouts)"))}
    return "user_id" in cols


def _ensure_legacy_user() -> int:
    """Create the legacy user if absent; return its id."""
    with SessionLocal() as db:
        legacy = db.scalar(select(User).where(User.email == LEGACY_USER_EMAIL))
        if legacy is None:
            legacy = User(email=LEGACY_USER_EMAIL, hashed_password=UNUSABLE_PASSWORD_HASH)
            db.add(legacy)
            db.commit()
            db.refresh(legacy)
            print(f"Created legacy user (id={legacy.id}, email={legacy.email}).")
        else:
            print(f"Legacy user already exists (id={legacy.id}).")
        return legacy.id


def _rebuild_workouts_with_fk(legacy_user_id: int) -> None:
    """Rebuild the workouts table with a NOT NULL user_id, backfilling rows."""
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE workouts RENAME TO workouts_pre_migration"))

        # Create the new table from the current ORM definition (includes user_id).
        Workout.__table__.create(bind=conn)

        result = conn.execute(
            text(
                "INSERT INTO workouts "
                "(id, name, type, duration_minutes, calories_burned, date, notes, user_id) "
                "SELECT id, name, type, duration_minutes, calories_burned, date, notes, :uid "
                "FROM workouts_pre_migration"
            ),
            {"uid": legacy_user_id},
        )
        conn.execute(text("DROP TABLE workouts_pre_migration"))
        print(f"Backfilled {result.rowcount} workout row(s) to user_id={legacy_user_id}.")


def main() -> None:
    # Creates the users table (and leaves the existing workouts table untouched).
    Base.metadata.create_all(bind=engine)

    if _workouts_already_migrated():
        print("workouts.user_id already present — nothing to do.")
        return

    legacy_user_id = _ensure_legacy_user()
    _rebuild_workouts_with_fk(legacy_user_id)
    print("Migration complete.")


if __name__ == "__main__":
    main()
