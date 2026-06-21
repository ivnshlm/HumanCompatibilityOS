from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app

# In-memory SQLite shared across connections for the whole test session.
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _setup_db() -> Generator[None, None, None]:
    # Import models so all tables register before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = _override_get_db
    # No context manager → lifespan/init_db (Postgres) is not triggered.
    yield TestClient(app)
    app.dependency_overrides.clear()


def bank_answers(value: int, level: str = "short") -> list[dict]:
    """Submission payload answering every question of a session level with `value`."""
    from app import question_bank

    return [{"question_id": qid, "value": value} for qid in question_bank.select_session(level)]


def bank_scores(value: int, level: str = "short") -> dict[str, int]:
    """{question_id: value} for a session level — direct input to compute_burnout_score."""
    from app import question_bank

    return {qid: value for qid in question_bank.select_session(level)}


def promote_role(email: str, role: str) -> None:
    """Test helper: grant a registered user a privileged role directly.

    Registration only ever creates Employees now, so tests that need an HR /
    admin / team_lead / ethics_reviewer set the role straight in the DB.
    """
    from app.models import Role, User

    with TestingSessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is not None:
            user.role = Role(role)
            db.commit()
