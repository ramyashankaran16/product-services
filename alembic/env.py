from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.db.base import Base
import app.models  # noqa: F401  (registers models on Base.metadata)

config = context.config
target_metadata = Base.metadata

# Tests pass an existing connection in; in that case leave logging alone.
external_connection = config.attributes.get("connection")

if config.config_file_name and external_connection is None:
    fileConfig(config.config_file_name)


def _database_url() -> str:
    from app.core.config import get_settings

    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(url=_database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    if external_connection is not None:
        _run(external_connection)
        return
    engine = create_engine(_database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        _run(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
