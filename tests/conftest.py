"""Shared test setup.

Environment variables are set here, before any `src` module is imported, because
`src.database` and `src.config` read them at import time. `load_dotenv()` never
overrides a variable that is already set, so these values win over `.env`.
"""
import os
import secrets
import uuid

from sqlalchemy.engine import make_url


def _test_database_url() -> str:
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        url = make_url(explicit)
    else:
        from dotenv import dotenv_values

        base = os.environ.get("DATABASE_URL") or dotenv_values(
            os.path.join(os.path.dirname(__file__), "..", ".env")
        ).get("DATABASE_URL")
        if not base:
            raise RuntimeError("Set TEST_DATABASE_URL to a local Postgres database ending in _test")
        url = make_url(base).set(database="grovii_test")
    # Safety: never run destructive test setup against a non-test database.
    if not (url.database or "").endswith("_test"):
        raise RuntimeError(f"Refusing to run tests against database '{url.database}' (name must end in _test)")
    return url.render_as_string(hide_password=False)


os.environ["DATABASE_URL"] = _test_database_url()
# A fresh random secret per test run. Never a real one.
os.environ["JWT_SECRET_KEY"] = secrets.token_urlsafe(64)
# A fake key so any LLM call that a test forgot to mock fails instead of costing money.
os.environ["OPENAI_API_KEY"] = "sk-test-not-a-real-key"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.database import Base, SessionLocal, engine  # noqa: E402
import src.models  # noqa: E402,F401  (registers all tables)
from src.models.users import User  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def user(db):
    u = User(
        username=f"u_{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="not-used",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def client():
    from src.main import app

    # No context manager: skips the app lifespan (which runs ad-hoc ALTER TABLEs).
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    email = f"{uuid.uuid4().hex[:8]}@example.com"
    password = "correct-horse-battery"
    r = client.post("/auth/register", json={"username": email.split("@")[0], "email": email, "password": password})
    assert r.status_code == 200, r.text
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


VALID_STORYBOARD = {
    "idea": "A 30 second espresso routine for busy mornings",
    "goal": "Educate",
    "tone": "Calm",
    "style": "Cinematic",
    "audience": "Coffee lovers",
    "duration": 30,
    "platform": "Instagram Reels",
    "language": "English",
}
