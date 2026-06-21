from collections.abc import Generator

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables. MVP-only: replaced by Alembic migrations later."""
    # Import models so they register on Base.metadata before create_all.
    from app import models  # noqa: F401
    from app.question_bank import validate_bank

    validate_bank()  # fail fast if the question bank resource is malformed
    _migrate_to_question_bank()
    Base.metadata.create_all(bind=engine)
    bootstrap_admins()


def _migrate_to_question_bank() -> None:
    """One-time cutover from the legacy int-indexed questionnaire to the bank.

    The old `questionnaire_answers` used `question_index` (1..15); the bank uses
    string `question_id`. SQLAlchemy create_all never alters existing tables, so
    on a deployed DB we drop the (disposable, pre-bank) questionnaire tables here
    and let create_all rebuild them with the new schema. Self-disabling: once the
    `question_id` column exists it never runs again, and on a fresh DB (tests)
    the table doesn't exist yet so it is a no-op.
    """
    insp = inspect(engine)
    if "questionnaire_answers" not in insp.get_table_names():
        return
    columns = {c["name"] for c in insp.get_columns("questionnaire_answers")}
    if "question_id" in columns:
        return  # already on the bank schema
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS recalibration_events CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS questionnaire_answers CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS questionnaires CASCADE"))


def bootstrap_admins() -> None:
    """Promote any existing users whose email is in INITIAL_ADMIN_EMAILS to admin.

    Idempotent: keeps a configured owner email as admin even after a reset, and
    never downgrades anyone. Runs on startup; new sign-ups with a whitelisted
    email are promoted at registration instead.
    """
    from app.models import Role, User

    emails = get_settings().initial_admin_email_list
    if not emails:
        return
    with SessionLocal() as db:
        users = db.scalars(select(User).where(func.lower(User.email).in_(emails))).all()
        changed = False
        for user in users:
            if user.role != Role.admin:
                user.role = Role.admin
                changed = True
        if changed:
            db.commit()
