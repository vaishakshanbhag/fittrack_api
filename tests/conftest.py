"""Shared pytest fixtures: an isolated in-memory DB, an API client, and auth helpers.

Every fixture here is function-scoped so each test gets a fresh, empty
database — no shared state, no need for transaction-rollback tricks, and no
risk of ever touching the real fittrack.db.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db import Base, get_db
from main import app
from models.user import UserIn
from services import auth, users


@pytest.fixture
def db_session():
    """A fresh in-memory SQLite session, isolated per test.

    StaticPool keeps the single in-memory connection alive for the fixture's
    lifetime (a plain in-memory engine would otherwise open a new, empty
    database on every checkout).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    """A TestClient wired to the isolated test database instead of fittrack.db.

    Deliberately NOT used as `with TestClient(app) as client`: entering the
    context manager would run main.py's lifespan, which calls
    Base.metadata.create_all against db.py's real engine (fittrack.db). Tables
    for the test database are already created above, so lifespan is neither
    needed nor wanted here.
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def make_user(db_session):
    """Factory fixture: create a user directly against the test DB, bypassing the API."""
    def _make_user(email="user@example.com", password="password123"):
        return users.create_user(db_session, UserIn(email=email, password=password))

    return _make_user


@pytest.fixture
def test_user(make_user):
    return make_user()


@pytest.fixture
def other_user(make_user):
    return make_user(email="other@example.com", password="password456")


@pytest.fixture
def auth_headers(test_user):
    token = auth.create_access_token(str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(other_user):
    token = auth.create_access_token(str(other_user.id))
    return {"Authorization": f"Bearer {token}"}
