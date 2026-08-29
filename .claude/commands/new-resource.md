---
description: Scaffold a full CRUD resource (schema, ORM model, service, routes, tests) following FitTrack conventions
argument-hint: <resource-name> <field:type> [field:type ...]
allowed-tools: Read, Write, Edit, Glob, Grep
---

You are scaffolding a new resource for the FitTrack API. The reference
pattern for every generated file is the existing Workout resource:
`models/workout.py`, `models/db_models.py` (the `Workout` class + the
`User.workouts` relationship), `services/workouts.py`, `routes/workouts.py`,
`tests/services/test_workouts_service.py`, `tests/api/test_workouts_routes.py`,
and its wiring in `main.py`. Read these five files first if you have not
already, so every generated file matches their structure, naming, and
docstring style exactly — not just in spirit.

Raw input: $ARGUMENTS

## 1. Parse input

Split into a resource name and a list of `field:type` pairs.

- Resource name: singular, snake_case (e.g. `meal`, `meal_plan`). If it's
  missing, or looks plural, or isn't a valid Python identifier, **stop and
  ask** the user for a corrected singular snake_case name.
- Each field is `name:type`, optionally suffixed with `?` to mark it
  optional/nullable (mirrors `Workout.notes: str | None = Field(None, ...)`),
  e.g. `notes:str?`. Field names must be valid Python identifiers and must
  not collide with the reserved names `id` or `user_id` (those are added
  automatically — do not let the user redefine them).

**Accepted types** (the only ones supported — map per this table):

| input type | Pydantic annotation | SQLAlchemy column |
|---|---|---|
| `str`      | `str`      | `String` |
| `int`      | `int`      | `Integer` |
| `float`    | `float`    | `Float` |
| `bool`     | `bool`     | `Boolean` |
| `date`     | `date` (import `date as date_type`, matching `workout.py`) | `Date` |
| `datetime` | `datetime` | `DateTime` |

If any field's type isn't in this table, or a field spec doesn't parse as
`name:type` / `name:type?`, **stop and ask** the user to clarify that field
rather than guessing a mapping. Do not proceed with partial output.

If there are zero fields, stop and ask — a resource needs at least one
field beyond `id`/`user_id`.

## 2. Derive names

- `Resource` — PascalCase of the singular name (`meal_plan` → `MealPlan`).
- `resource` — the singular snake_case name, used for the model file and
  route-param name (`meal_plan_id`).
- `resources` — plural, via standard English rules: ends in
  `y` (not preceded by a vowel) → `ies`; ends in `s`/`x`/`z`/`ch`/`sh` →
  `es`; otherwise `+s`. Used for the table name, route path, service/route/
  test file names, and the router's `tags`.

Check `models/db_models.py` for a `__tablename__` collision and
`models/`, `services/`, `routes/` for an existing file with the derived
name. If anything already exists, **stop and ask** whether to overwrite or
pick a different name — do not silently clobber existing work.

## 3. Generate `models/<resource>.py`

Follow `models/workout.py` exactly: a `<Resource>Base` with every field as
a `Field(..., description=...)` (optional fields get `None` default and
`| None` type), then empty `<Resource>In(Base)` and
`<Resource>Update(Base)` subclasses (full-replace semantics, same as
`WorkoutUpdate` — no partial-update variant), then `<Resource>Out(Base)`
with `model_config = ConfigDict(from_attributes=True)` plus `id: int` and
`user_id: int` fields with descriptions. Match docstring wording style.

## 4. Extend `models/db_models.py`

Add a new `class <Resource>(Base)` following the `Workout` class exactly:
`__tablename__ = "<resources>"`, `id` primary key, one `mapped_column` per
field with the SQLAlchemy type from the table above (`nullable=False`
unless the field was marked optional), a `user_id` FK
(`ForeignKey("users.id"), nullable=False, index=True`), and a
`user: Mapped["User"] = relationship(back_populates="<resources>")`.

Add the matching `back_populates` side to `User`:
`<resources>: Mapped[list["<Resource>"]] = relationship(back_populates="user")`,
placed next to the existing `workouts` relationship. Do **not** add any
`cascade=` argument — deletion policy belongs in the service layer per
`CLAUDE.md`'s Deletion & data retention convention, not the ORM.

Add any new SQLAlchemy type imports (`Float`, `Boolean`, `DateTime`) to the
existing `from sqlalchemy import ...` line only if the fields need them and
they aren't already imported.

## 5. Generate `services/<resources>.py`

Mirror `services/workouts.py` structure precisely:

- `class <Resource>NotFoundError(NotFoundError)` with an `__init__(self,
  <resource>_id: int)` storing the id and a client-safe detail message.
- `create(db, payload, user_id)` — `<Resource>(**payload.model_dump(),
  user_id=user_id)`, add/commit/refresh, return
  `<Resource>Out.model_validate(...)`.
- `list_all(db, user_id)` — scoped to `user_id`, same `select(...).where(...)`
  pattern.
- `get(db, <resource>_id, user_id)` — `db.get`, then the
  `is None or .user_id != user_id` → raise pattern (a row owned by another
  user reads as not-found, same comment as `workouts.get`).
- `update(db, <resource>_id, payload, user_id)` — same ownership check,
  then `for field, value in payload.model_dump().items(): setattr(...)`,
  commit, refresh.
- `delete(db, <resource>_id, user_id)` — same ownership check, then a
  **plain** `db.delete(...)`; `db.commit()`. No retention/reassignment
  logic — that pattern in `services/users.py` is specific to deleting a
  *user* and its dependent rows, not to every resource's own deletion.

Match docstrings verbatim in style (one-line summaries, ownership note on
`get`).

## 6. Generate `routes/<resources>.py`

Mirror `routes/workouts.py` exactly: `router = APIRouter(tags=["<resources>"])`,
five thin handlers (`POST /<resources>`, `GET /<resources>`,
`GET /<resources>/{<resource>_id}`, `PUT /<resources>/{<resource>_id}`,
`DELETE /<resources>/{<resource>_id}`), each with
`current_user: User = Depends(get_current_user)` and
`db: Session = Depends(get_db)`, a docstring, and a single call into
`services.<resources>`. `POST` returns `status_code=status.HTTP_201_CREATED`;
`DELETE` returns `status_code=status.HTTP_204_NO_CONTENT` and no body.

## 7. Wire into `main.py`

Add `<resources>` to the `from routes import ...` line (keep alphabetical
order among `auth, health, workouts, ...`) and add
`app.include_router(<resources>.router)` next to the existing
`include_router` calls, same position in the alphabetical grouping.

## 8. Generate tests

`tests/services/test_<resources>_service.py` — mirror
`tests/services/test_workouts_service.py`: a `_<resource>_data(**overrides)`
helper with one sample value per field, then tests for create, list scoped
to user, get (success / not-found / owned-by-other-user), update (success /
not-found / owned-by-other-user), delete (success / owned-by-other-user).
Use the existing `db_session`, `test_user`, `other_user` fixtures from
`tests/conftest.py` — do not redefine them.

`tests/api/test_<resources>_routes.py` — mirror
`tests/api/test_workouts_routes.py`: a module-level `<RESOURCE>_PAYLOAD`
dict, then the same endpoint-level cases (create/list-scoped/get/update/
delete, each success and 404 variant, plus an invalid-payload → 422 case
using whichever field has a validation constraint, and an
unauthenticated → 401 case). Use the existing `client`, `auth_headers`,
`other_auth_headers` fixtures — do not redefine them.

## 9. Hand off verification to the user

Do not run the test command yourself — shell commands, `uv run` ones
especially, have hung in this terminal integration before and needed a
manual interrupt. Instead:

1. Print the exact command:
   ```
   uv run pytest tests/services/test_<resources>_service.py tests/api/test_<resources>_routes.py -v
   ```
2. Ask the user to run it in their own terminal and paste the output back.
3. Once you have that output, if anything failed, fix the generated code
   (not the tests), then print the command again (narrow it with
   `-k <test_name>` once most tests pass, to keep re-runs short) and wait
   for the user to paste the next result. Don't assume pass/fail — only
   move to step 10 once the user has confirmed a green run.
4. If a failure traces back to an ambiguous assumption from step 1 or 2,
   stop and ask the user directly rather than iterating further.

## 10. CLAUDE.md

Only touch `CLAUDE.md` if this resource introduced something genuinely new
that isn't already covered by its existing conventions (e.g. a field type
never used before, like `bool`/`float`/`datetime`, needing a documented
SQLAlchemy mapping). Don't restate existing conventions. If you find such a
case, propose the specific addition to the user and wait for a yes before
editing the file — do not edit `CLAUDE.md` unasked.

## 11. Summary

List every file created or modified, and the exact `uv run pytest` command
used to verify, so the user can re-run it themselves.
