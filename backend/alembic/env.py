"""Alembic migration environment for Human Compatibility OS.

The DB URL is resolved from app settings (DATABASE_URL env var) so migrations
always target the same database as the running app. For local autogenerate you
can override it with `-x url=...` (e.g. an empty SQLite file). When invoked
programmatically from `app.db.run_migrations`, an existing connection may be
passed via `config.attributes["connection"]` to reuse the app engine.
"""

from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

# Import the app metadata. Importing app.models registers every table on Base.
from app import models  # noqa: F401
from app.config import get_settings
from app.db import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    x = context.get_x_argument(as_dictionary=True)
    if x.get("url"):
        return x["url"]
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    engine = create_engine(_url(), poolclass=pool.NullPool, future=True)
    with engine.connect() as conn:
        _run(conn)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
