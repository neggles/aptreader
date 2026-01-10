# ruff: isort:skip-file
import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# trigger DB monkey-patching
from aptreader.db import NAMING_CONVENTION

# this needs to be _after_ aptreader.db is imported
import reflex as rx  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# Try to set the SQLAlchemy URL from the Reflex config
try:
    from rxconfig import DB_URL  # type: ignore[import]

    config.set_main_option("sqlalchemy.url", DB_URL)
    logger.info("Loaded rxconfig for Alembic migrations.")
except ImportError:
    logger.warning("Could not import rxconfig, using alembic.ini settings.")
    pass

db_url = config.get_main_option("sqlalchemy.url")
if db_url is None:
    raise RuntimeError("Database URL could not be determined for Alembic migrations.")
logger.info(f"Using database URL: {db_url}")

is_sqlite = "sqlite" in db_url
dialect_opts = {"paramstyle": "named"} if is_sqlite else None

# get the target metadata from Reflex models
target_metadata = rx.model.ModelRegistry.get_metadata()

# make sure our monkeypatch worked
naming_keys = list(target_metadata.naming_convention.keys())
if any(key not in naming_keys for key in NAMING_CONVENTION.keys()):
    raise RuntimeError("Alembic env.py metadata naming convention monkeypatch failed.")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts=dialect_opts,
        render_as_batch=is_sqlite,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=is_sqlite,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
