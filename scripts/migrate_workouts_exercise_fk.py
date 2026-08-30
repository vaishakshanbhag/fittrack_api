"""One-off migration: replace ``workouts.type``/``workouts.name`` with a
required, NOT NULL ``workouts.exercise_id`` foreign key into the new
``exercises`` catalog table.

This project has no migration framework (see ``scripts/migrate_add_users.py``
for the pattern this follows) — schema changes to a table that already holds
data need an explicit, idempotent one-off script.

Strategy (agreed in the issue this closes):
    1. Back up ``fittrack.db`` before touching anything.
    2. Ensure the ``exercises`` catalog is populated (importing it via
       ``scripts/import_exercises.py`` if it isn't), including the
       "__unmatched__" sentinel row used as a fallback below.
    3. For every existing ``workouts`` row, fuzzy-match its old ``name``
       against ``Exercise.name`` (narrowed by the old ``type`` where it maps
       cleanly to a catalog ``category``) using stdlib ``difflib``. Anything
       that doesn't match confidently is assigned to the sentinel exercise
       rather than guessed, so it stays easy to find and re-triage later.
    4. Rebuild ``workouts`` with the new NOT NULL ``exercise_id`` column and
       without ``type``/``name`` (SQLite can't alter this in place), copying
       every row with its computed ``exercise_id``.

Pass ``--dry-run`` to print the full match report without changing anything —
recommended before the real run, since the rebuild is irreversible (the
``.bak`` file is your undo).

Pass ``--llm-second-pass`` to additionally send every UNMATCHED/LOW-CONFIDENCE
row to Claude Haiku 4.5 (one Message Batches job) for a semantic second
opinion — difflib only sees character overlap, so it can be fooled by two
unrelated exercises that happen to share a lot of letters (or miss real
matches phrased differently). This is optional: it requires the ``anthropic``
package (``uv sync --extra llm``) and an ``ANTHROPIC_API_KEY``, and any
failure (missing dependency/key, timeout, a bad response for one row) leaves
that row's difflib result untouched rather than failing the migration.

The script is idempotent: re-running it is a no-op once ``exercise_id`` exists.

Run from the project root:
    ``uv run python scripts/migrate_workouts_exercise_fk.py [--dry-run] [--llm-second-pass]``
"""

import argparse
import difflib
import os
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

# Allow running as a plain script by putting the project root (for app
# imports) and this scripts/ directory (for the sibling import_exercises
# module) on the import path.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import import_exercises  # noqa: E402
from sqlalchemy import select, text  # noqa: E402

from db import Base, SessionLocal, engine  # noqa: E402
from models.db_models import Exercise, Workout  # noqa: E402

DB_PATH = _PROJECT_ROOT / "fittrack.db"
BACKUP_PATH = _PROJECT_ROOT / "fittrack.db.bak"

# Maps a legacy workout.type value to the set of Exercise.category values
# worth narrowing the fuzzy match to. Anything not listed here (or with no
# candidates in that category) falls back to searching the whole catalog.
CATEGORY_MAP = {
    "cardio": {"cardio"},
    "strength": {"strength", "powerlifting", "olympic weightlifting", "strongman"},
}

FUZZY_MATCH_CUTOFF = 0.6
CONFIDENT_MATCH_CUTOFF = 0.75

# LLM second-pass settings (only used with --llm-second-pass).
LLM_MODEL = "claude-haiku-4-5-20251001"
LLM_CANDIDATE_COUNT = 12
LLM_MAX_TOKENS = 20
LLM_POLL_INTERVAL_SECONDS = 5
LLM_POLL_TIMEOUT_SECONDS = 600


def _workouts_already_migrated() -> bool:
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(workouts)"))}
    return "exercise_id" in cols


def _fetch_legacy_rows() -> list[dict]:
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT id, name, type, duration_minutes, calories_burned, "
                "date, notes, user_id FROM workouts"
            )
        )
        return [dict(row._mapping) for row in result]


def _load_exercises(db) -> tuple[list[Exercise], dict[str, list[Exercise]]]:
    rows = db.scalars(
        select(Exercise).where(Exercise.external_id != import_exercises.UNMATCHED_EXTERNAL_ID)
    ).all()
    by_category = defaultdict(list)
    for row in rows:
        by_category[row.category].append(row)
    return rows, by_category


def _unmatched_exercise_id(db) -> int:
    exercise = db.scalar(
        select(Exercise).where(Exercise.external_id == import_exercises.UNMATCHED_EXTERNAL_ID)
    )
    if exercise is None:
        raise RuntimeError(
            "Sentinel exercise not found. Run scripts/import_exercises.py first."
        )
    return exercise.id


def _candidates_for_type(
    old_type: str | None, all_rows: list[Exercise], by_category: dict[str, list[Exercise]]
) -> list[Exercise]:
    categories = CATEGORY_MAP.get((old_type or "").strip().lower())
    if not categories:
        return all_rows
    candidates = [row for category in categories for row in by_category.get(category, [])]
    return candidates or all_rows


def _match_exercise(
    old_type: str | None,
    old_name: str | None,
    all_rows: list[Exercise],
    by_category: dict[str, list[Exercise]],
) -> tuple[Exercise | None, float]:
    """Return the best-matching exercise and its similarity score (0-1).

    The candidate with the highest score always wins; the caller decides what
    to do with a low score (a returned match's score can still be below
    FUZZY_MATCH_CUTOFF, in which case it should be treated as no match).
    """
    candidates = _candidates_for_type(old_type, all_rows, by_category)
    query = (old_name or "").lower()
    best_row: Exercise | None = None
    best_score = 0.0
    for row in candidates:
        score = difflib.SequenceMatcher(None, query, row.name.lower()).ratio()
        if score > best_score:
            best_row, best_score = row, score
    if best_score < FUZZY_MATCH_CUTOFF:
        return None, best_score
    return best_row, best_score


def _build_mapping(
    rows: list[dict],
    all_rows: list[Exercise],
    by_category: dict[str, list[Exercise]],
    unmatched_id: int,
) -> tuple[dict[int, int], list[dict]]:
    """Compute the workout.id -> exercise_id mapping and print a match report.

    Each row is tagged CONFIDENT (score >= 0.75), LOW-CONFIDENCE (0.6-0.75,
    worth a manual look), or UNMATCHED (below 0.6, assigned the sentinel).
    Returns the mapping plus the LOW-CONFIDENCE/UNMATCHED rows, which are the
    ones worth sending through the optional LLM second pass.
    """
    mapping: dict[int, int] = {}
    review_rows: list[dict] = []
    confident = low_confidence = unmatched = 0
    for row in rows:
        match, score = _match_exercise(row["type"], row["name"], all_rows, by_category)
        if match is None:
            mapping[row["id"]] = unmatched_id
            unmatched += 1
            review_rows.append(row)
            tier = "UNMATCHED -> sentinel"
        elif score >= CONFIDENT_MATCH_CUTOFF:
            mapping[row["id"]] = match.id
            confident += 1
            tier = f"CONFIDENT ({score:.2f}) -> {match.name!r}"
        else:
            mapping[row["id"]] = match.id
            low_confidence += 1
            review_rows.append(row)
            tier = f"LOW-CONFIDENCE ({score:.2f}) -> {match.name!r}"
        print(f"  workout#{row['id']}: type={row['type']!r} name={row['name']!r} -> {tier}")
    print(
        f"Confident: {confident}, low-confidence: {low_confidence}, "
        f"unmatched (sentinel fallback): {unmatched}  (total {len(rows)})"
    )
    return mapping, review_rows


def _top_candidates(
    old_type: str | None,
    old_name: str | None,
    all_rows: list[Exercise],
    by_category: dict[str, list[Exercise]],
    limit: int = LLM_CANDIDATE_COUNT,
) -> list[Exercise]:
    """The `limit` catalog exercises most similar to old_name by difflib ratio.

    Used to keep the LLM prompt small: difflib is good enough to shortlist
    plausible candidates even when it can't confidently pick the winner.
    """
    candidates = _candidates_for_type(old_type, all_rows, by_category)
    query = (old_name or "").lower()
    return sorted(
        candidates,
        key=lambda c: difflib.SequenceMatcher(None, query, c.name.lower()).ratio(),
        reverse=True,
    )[:limit]


def _llm_prompt(row: dict, candidates: list[Exercise]) -> str:
    options = "\n".join(f"{i}. {c.name} (category: {c.category})" for i, c in enumerate(candidates, 1))
    return (
        f"A legacy workout log entry has the free-text type {row['type']!r} and "
        f"name {row['name']!r}. Which of the following catalog exercises, if any, "
        "is the same real-world movement?\n\n"
        f"{options}\n\n"
        "Respond with ONLY the number of the best match, or the single word "
        "NONE if none of these are plausibly the same exercise. No other text."
    )


def _parse_llm_choice(text: str, candidate_count: int) -> int | None:
    """Parse the model's reply into a 1-based candidate index, or None for NONE/unparseable."""
    text = text.strip()
    if text.upper().startswith("NONE"):
        return None
    try:
        choice = int(text.split()[0])
    except (ValueError, IndexError):
        return None
    return choice if 1 <= choice <= candidate_count else None


def _run_llm_second_pass(
    review_rows: list[dict],
    all_rows: list[Exercise],
    by_category: dict[str, list[Exercise]],
    unmatched_id: int,
    mapping: dict[int, int],
) -> None:
    """Send UNMATCHED/LOW-CONFIDENCE rows to Haiku 4.5 for a second opinion.

    Mutates `mapping` in place for rows the batch resolves. Any row the batch
    can't resolve (missing dependency/key, timeout, per-row failure) keeps
    its original difflib result — this pass only ever improves on difflib,
    never blocks the migration if it's unavailable.
    """
    if not review_rows:
        return

    try:
        import anthropic
    except ImportError:
        print(
            "anthropic package not installed — skipping LLM second pass "
            "(install with `uv sync --extra llm`). Keeping difflib results for these rows."
        )
        return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set — skipping LLM second pass. Keeping difflib results.")
        return

    client = anthropic.Anthropic()
    row_candidates = {row["id"]: _top_candidates(row["type"], row["name"], all_rows, by_category)
                      for row in review_rows}

    print(f"Submitting {len(review_rows)} row(s) to {LLM_MODEL} as one batch job...")
    try:
        batch = client.messages.batches.create(
            requests=[
                {
                    "custom_id": f"workout-{row['id']}",
                    "params": {
                        "model": LLM_MODEL,
                        "max_tokens": LLM_MAX_TOKENS,
                        "messages": [
                            {"role": "user", "content": _llm_prompt(row, row_candidates[row["id"]])}
                        ],
                    },
                }
                for row in review_rows
            ]
        )
    except Exception as exc:  # noqa: BLE001 - any API/network failure is non-fatal here
        print(f"Failed to submit LLM batch ({exc}) — keeping difflib results for these rows.")
        return

    deadline = time.monotonic() + LLM_POLL_TIMEOUT_SECONDS
    while True:
        status = client.messages.batches.retrieve(batch.id)
        if status.processing_status == "ended":
            break
        if time.monotonic() > deadline:
            print(
                f"LLM batch {batch.id} still {status.processing_status} after "
                f"{LLM_POLL_TIMEOUT_SECONDS}s — keeping difflib results for these rows."
            )
            return
        time.sleep(LLM_POLL_INTERVAL_SECONDS)

    resolved = updated = 0
    for result in client.messages.batches.results(batch.id):
        workout_id = int(result.custom_id.removeprefix("workout-"))
        candidates = row_candidates[workout_id]
        if result.result.type != "succeeded":
            print(f"  workout#{workout_id}: LLM request {result.result.type} — kept difflib result.")
            continue
        text = "".join(
            block.text for block in result.result.message.content if block.type == "text"
        )
        choice = _parse_llm_choice(text, len(candidates))
        resolved += 1
        if choice is None:
            mapping[workout_id] = unmatched_id
            print(f"  workout#{workout_id}: LLM says NONE -> sentinel")
        else:
            chosen = candidates[choice - 1]
            mapping[workout_id] = chosen.id
            updated += 1
            print(f"  workout#{workout_id}: LLM-MATCHED -> {chosen.name!r}")
    print(
        f"LLM second pass resolved {resolved}/{len(review_rows)} row(s) "
        f"({updated} matched to a real exercise, {resolved - updated} confirmed NONE)."
    )


def _rebuild_workouts(mapping: dict[int, int], rows: list[dict]) -> None:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE workouts RENAME TO workouts_pre_migration"))

        # SQLite keeps each index's original name after a table rename (index
        # names are schema-global, not per-table), so workouts_pre_migration
        # still owns e.g. ix_workouts_user_id. Creating the new workouts table
        # below declares the same index names, which would collide. Dropping
        # them here is safe: workouts_pre_migration itself is dropped a few
        # lines down, taking any data-integrity concern with it.
        existing_indexes = conn.execute(text("PRAGMA index_list(workouts_pre_migration)")).all()
        for index in existing_indexes:
            conn.execute(text(f'DROP INDEX IF EXISTS "{index[1]}"'))

        Workout.__table__.create(bind=conn)
        if rows:
            conn.execute(
                text(
                    "INSERT INTO workouts "
                    "(id, duration_minutes, calories_burned, date, notes, user_id, exercise_id) "
                    "VALUES (:id, :duration_minutes, :calories_burned, :date, :notes, "
                    ":user_id, :exercise_id)"
                ),
                [
                    {
                        "id": row["id"],
                        "duration_minutes": row["duration_minutes"],
                        "calories_burned": row["calories_burned"],
                        "date": row["date"],
                        "notes": row["notes"],
                        "user_id": row["user_id"],
                        "exercise_id": mapping[row["id"]],
                    }
                    for row in rows
                ],
            )
        conn.execute(text("DROP TABLE workouts_pre_migration"))
    print(f"Rebuilt workouts table with exercise_id for {len(rows)} row(s).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the match report without changing the database.",
    )
    parser.add_argument(
        "--llm-second-pass",
        action="store_true",
        help=(
            "Send UNMATCHED/LOW-CONFIDENCE rows to Claude Haiku 4.5 (one batch job) "
            "for a semantic second opinion. Requires `anthropic` and ANTHROPIC_API_KEY; "
            "any failure falls back to the difflib result for the affected rows."
        ),
    )
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)

    if _workouts_already_migrated():
        print("workouts.exercise_id already present — nothing to do.")
        return

    rows = _fetch_legacy_rows()

    with SessionLocal() as db:
        if db.scalar(select(Exercise.id).limit(1)) is None:
            print("No exercises found — importing from free-exercise-db first.")
            import_exercises.main()

        if not rows:
            print("No existing workouts to migrate.")
            mapping: dict[int, int] = {}
        else:
            all_rows, by_category = _load_exercises(db)
            unmatched_id = _unmatched_exercise_id(db)
            mapping, review_rows = _build_mapping(rows, all_rows, by_category, unmatched_id)
            if args.llm_second_pass:
                _run_llm_second_pass(review_rows, all_rows, by_category, unmatched_id, mapping)

    if args.dry_run:
        print("Dry run — no changes made. Re-run without --dry-run to apply.")
        return

    if DB_PATH.exists():
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print(f"Backed up {DB_PATH.name} -> {BACKUP_PATH.name}")

    _rebuild_workouts(mapping, rows)
    print("Migration complete.")


if __name__ == "__main__":
    main()
