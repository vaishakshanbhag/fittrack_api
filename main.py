from contextlib import asynccontextmanager

from fastapi import FastAPI

from db import Base, engine
from models import db_models  # noqa: F401 - register ORM models on Base.metadata
from routes import auth, health, workouts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="FitTrack API", lifespan=lifespan)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(workouts.router)


@app.get("/")
def root():
    """Root endpoint — returns a welcome message."""
    return {"message": "Welcome to the FitTrack API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
