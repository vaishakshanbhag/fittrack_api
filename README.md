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

## Run

```powershell
uv run uvicorn main:app --reload
```

The API will be available at http://127.0.0.1:8000.
Interactive docs: http://127.0.0.1:8000/docs

## Endpoints

- `GET /` — welcome message
- `GET /health` — returns `{"status": "ok"}`
