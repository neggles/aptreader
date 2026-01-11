"""Database helpers."""

import logging

import sqlalchemy as sa
import wrapt
from sqlalchemy.dialects.sqlite.aiosqlite import AsyncAdapt_aiosqlite_connection
from sqlalchemy.engine import Engine
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.event import listens_for
from sqlalchemy.pool import ConnectionPoolEntry

from .constants import DB_URL
from .models import *  # noqa: F403

logger = logging.getLogger(__name__)

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_`%(constraint_name)s`",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


@listens_for(Engine, "connect", insert=True)
def on_engine_connect(
    dbapi_connection: DBAPIConnection,
    connection_record: ConnectionPoolEntry,
) -> None:
    """Event listener for synchronous engine connections."""
    try:
        if not dbapi_connection:
            return

        if "sqlite://" in DB_URL:
            if isinstance(dbapi_connection, AsyncAdapt_aiosqlite_connection):
                ac = dbapi_connection.isolation_level
                dbapi_connection.isolation_level = None
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
                dbapi_connection.isolation_level = ac
            else:
                # the sqlite3 driver will not set PRAGMA foreign_keys if autocommit=False; set to True temporarily
                ac = dbapi_connection.autocommit
                dbapi_connection.autocommit = True

                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

                # restore previous autocommit setting
                dbapi_connection.autocommit = ac
            logger.debug(f"SQLite PRAGMA foreign_keys=ON set for connection {dbapi_connection!r}")
        else:
            logger.debug("No PRAGMA settings applied; not an SQLite database.")
    except Exception as e:
        logger.exception(f"Error setting SQLite PRAGMA: {e}")
        raise e


# monkey-patch Reflex ModelRegistry to include naming conventions in metadata
@wrapt.patch_function_wrapper("reflex.model", "ModelRegistry.get_metadata")
def get_metadata_wrapper(wrapped, instance, args, kwargs):
    """Wrapper to get metadata for Alembic."""
    metadata: sa.MetaData = wrapped(*args, **kwargs)
    metadata.naming_convention = NAMING_CONVENTION
    return metadata
