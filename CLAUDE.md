# CLAUDE.md

Guidance for working in the FitTrack API codebase.

## Project structure

```
fittrack_api/
├── main.py            # App entry point; creates the FastAPI app and includes routers
├── db.py              # SQLAlchemy engine, session factory, get_db dependency, Base
├── config.py          # App/auth config (SECRET_KEY, JWT algorithm, token expiry)
├── deps.py            # Shared FastAPI dependencies (e.g. get_current_user)
├── routes/            # API route modules — one file per resource/domain
├── models/            # Pydantic schemas + SQLAlchemy ORM models
├── services/          # Business logic (create as needed, one module per domain)
├── scripts/           # One-off maintenance/migration scripts
├── pyproject.toml     # Project metadata and dependencies
├── uv.lock            # Locked dependency versions (committed)
└── .venv/             # uv-managed virtual environment (git-ignored)
```

## Conventions

### Routes
- Every route file lives in `routes/` and defines an `APIRouter`.
- **Always** give the router a `tags` argument so endpoints are grouped in the
  OpenAPI docs, e.g. `router = APIRouter(tags=["workouts"])`.
- Register each router in `main.py` via `app.include_router(...)`.

### Thin handlers
- Endpoint handlers stay **thin**: parse/validate the request, call a service
  function, return the result. No business logic in the handler.
- Business logic goes in a matching module under `services/` (e.g. the
  `routes/workouts.py` endpoints call functions in `services/workouts.py`).

### Error mapping
- Services raise **domain exceptions**, not HTTP errors. Anything that means
  "resource does not exist" subclasses `NotFoundError` (in `errors.py`) and
  carries a client-safe `detail` message — e.g. `WorkoutNotFoundError`,
  `UserNotFoundError`.
- A single exception handler in `main.py` maps `NotFoundError` (and its
  subclasses) to a `404`. **Handlers must not repeat `try/except` → 404
  boilerplate** — just call the service and let the exception propagate.

### Docstrings
- **Every** endpoint handler has a docstring describing what it does. FastAPI
  surfaces this as the endpoint description in the interactive docs.

### Models
- Request/response bodies are Pydantic models defined in `models/`, one file
  per resource (e.g. `models/workout.py`, `models/user.py`).
- Keep validation in the models rather than in handlers.

### ORM models and relationships
- SQLAlchemy ORM models (the database tables) all live together in
  `models/db_models.py`, sharing the `Base` from `db.py`. Keeping them in one
  module lets relationships reference each other by class without import cycles.
- Model **relationships** (e.g. `relationship(...)` / `ForeignKey(...)`) are
  defined here too. Foreign keys that own a resource are `nullable=False`; the
  one-to-many is declared with `back_populates` on both sides (see
  `User.workouts` ↔ `Workout.user`).
- **Do not put blanket delete cascades** (e.g. `cascade="all, delete-orphan"`)
  on relationships. Deletion policy — cascade vs. reassign/retain — is a
  business decision that belongs in the service layer, not baked into the ORM.
  See the deletion convention below.
- The Pydantic schemas in `models/*.py` are the API contract; the ORM models in
  `models/db_models.py` define storage. Never expose sensitive columns (e.g.
  `hashed_password`) through an output schema. Email fields use Pydantic's
  `EmailStr` for format validation (requires the `email-validator` dependency).

### Reference/catalog tables
- Some tables are **shared, non-user-owned reference data** rather than
  per-user resources — e.g. `Exercise`, a catalog of exercises referenced by
  `Workout.exercise_id`. These are never created or modified through the API:
  they're populated once by a one-off script (see `scripts/import_exercises.py`,
  which seeds `Exercise` from the free-exercise-db public domain dataset) and
  exposed only through read-only routes/services (`routes/exercises.py`,
  `services/exercises.py` — `list_all`/`get`, no `create`/`update`/`delete`).
- A resource that references catalog data still follows the normal
  FK/relationship convention (`ForeignKey`, `back_populates` on both sides),
  it just has no ownership check in its service — the catalog isn't scoped to
  a user, so there's nothing to check against.

### Deletion & data retention
- Choices about what happens to a resource's dependent rows on delete live in
  the **service layer**, not in ORM cascade rules. For example,
  `services/users.py::delete_user(db, user_id, delete_data=False)`:
  - `delete_data=True` — delete the user and their workouts.
  - `delete_data=False` (default) — retain the workouts by reassigning them to a
    freshly created **anonymized placeholder** user (unusable password hash `"!"`,
    a unique generated email like `deleted-user-{id}@fittrack.local`), then
    delete the original user.
  - The placeholder is built as a raw ORM `User(...)`, never via `UserIn`: its
    `@fittrack.local` address is a reserved special-use domain that Pydantic's
    `EmailStr` rejects, so it only works by bypassing that validation. This is
    fine as long as nothing constructs a `UserIn`/`UserOut` for a placeholder —
    if a future route ever serializes one through `UserOut`, `EmailStr` will
    reject it there too.
- Because there is no ORM cascade, a service that deletes an owner must either
  delete its children explicitly or reassign them (moving `child.user` keeps
  both sides of the relationship in sync so SQLAlchemy won't try to NULL a
  `NOT NULL` foreign key).

### Migrations
- There is **no migration framework**. On startup `Base.metadata.create_all`
  creates any *missing* tables but never alters existing ones.
- Schema changes to a table that already holds data (adding a NOT NULL column,
  a required foreign key, etc.) need an explicit one-off script in `scripts/`.
  Such scripts must be **idempotent** and must **preserve existing data** —
  back up `fittrack.db` and backfill rows rather than dropping them. See
  `scripts/migrate_add_users.py` for the pattern.
- When backfilling a required FK from prior free-text data (no natural,
  exact mapping), see `scripts/migrate_workouts_exercise_fk.py`: fuzzy-match
  each row against the new reference table and fall back to an explicit
  sentinel row for anything below the confidence cutoff, rather than
  guessing — this keeps low-confidence backfills easy to find and re-triage
  later instead of silently baking a wrong guess into the data.

### Authentication
- The API uses **JWT bearer auth** (OAuth2 password flow). Auth primitives
  (password hashing via `pwdlib`/argon2, JWT create/decode via `PyJWT`) live in
  `services/auth.py`; the request-layer guard `get_current_user` lives in
  `deps.py`.
- **Protected routes take `current_user: User = Depends(get_current_user)`.**
  Anything user-scoped must be guarded this way.
- **Never trust an owner id from the request body.** A resource's `user_id` is
  derived from `current_user.id`, not accepted as input — e.g. `WorkoutIn` has
  no `user_id`; the service stamps it from the authenticated user. Ownership is
  enforced in the service (a row owned by another user is treated as `404`).
- `/auth/signup` returns `UserOut` (no token); `/auth/login` uses
  `OAuth2PasswordRequestForm` (email in the `username` field) and returns a
  `Token`. `tokenUrl` is `auth/login` so Swagger's "Authorize" button works.
- **Secret key:** signing uses `FITTRACK_SECRET_KEY`. If unset, the app hard-
  fails when `FITTRACK_ENV=prod` and otherwise falls back to a fixed insecure
  dev key with a stderr warning. Never commit a real key. Token expiry defaults
  to 7 days (`FITTRACK_ACCESS_TOKEN_EXPIRE_MINUTES`); JWTs are stateless and
  cannot be revoked, so the expiry is the security window.
- Anonymized/placeholder users (unusable hash `"!"`) can never authenticate, so
  their workouts are unreachable via the API by design.

## Example route

```python
from fastapi import APIRouter

from models.workout import WorkoutIn, WorkoutOut
from services import workouts

router = APIRouter(tags=["workouts"])


@router.post("/workouts", response_model=WorkoutOut)
def create_workout(payload: WorkoutIn):
    """Create a new workout for the current user."""
    return workouts.create(payload)
```

## Running the app

This project uses [uv](https://docs.astral.sh/uv/) for environment and
dependency management.

```powershell
uv run uvicorn main:app --reload
```

`uv run` automatically syncs the environment from `uv.lock` before running, so
there's no separate activate/install step. (If you prefer, you can still
activate the environment manually with `.venv\Scripts\Activate.ps1`.)

- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs

## Dependencies

- Dependencies are declared in `pyproject.toml` and pinned in `uv.lock`.
- Add a package: `uv add <package>` (updates `pyproject.toml` and `uv.lock`).
- Remove a package: `uv remove <package>`.
- Sync the environment to the lockfile: `uv sync`.
- Commit both `pyproject.toml` and `uv.lock`.
