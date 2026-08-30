from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from db import Base, engine
from errors import NotFoundError
from models import db_models  # noqa: F401 - register ORM models on Base.metadata
from routes import auth, exercises, health, journal_entries, measurements, workouts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="FitTrack API", lifespan=lifespan)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    """Map any domain NotFoundError to a 404 response."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.detail},
    )


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(exercises.router)
app.include_router(journal_entries.router)
app.include_router(measurements.router)
app.include_router(workouts.router)


@app.get("/")
def root():
    """Root endpoint — returns a welcome message."""
    return {"message": "Welcome to the FitTrack API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
