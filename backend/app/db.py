from collections.abc import Generator

from sqlalchemy import create_engine, func, select
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

    Base.metadata.create_all(bind=engine)
    bootstrap_admins()


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
