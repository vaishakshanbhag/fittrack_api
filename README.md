# FitTrack API

A FastAPI backend.

## Structure

```
fittrack_api/
├── main.py            # App entry point
├── models/            # Pydantic / data models
├── routes/            # API route modules
│   └── health.py      # /health endpoint
├── pyproject.toml
├── uv.lock
└── README.md
```

## Setup

This project uses [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
```

## Secret scanning

A pre-commit hook runs [gitleaks](https://github.com/gitleaks/gitleaks) on
every commit to catch accidentally committed secrets. The binary isn't
checked in — download the `gitleaks_<version>_windows_x64.zip` release for
your platform from the [gitleaks releases page](https://github.com/gitleaks/gitleaks/releases),
place `gitleaks.exe` (or `gitleaks` on macOS/Linux) at `.tools/gitleaks.exe`,
then run:

```powershell
uv run pre-commit install
```

Without the binary at that path, the hook will fail to run on commit.

## Run

```powershell
uv run uvicorn main:app --reload
```

The API will be available at http://127.0.0.1:8000.
Interactive docs: http://127.0.0.1:8000/docs

## Endpoints

- `GET /` — welcome message
- `GET /health` — returns `{"status": "ok"}`
