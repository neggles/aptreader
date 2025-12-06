"""Database helpers."""

import logging

import sqlalchemy as sa
import wrapt
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
        if "sqlite://" in DB_URL:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            logger.debug("Enabled SQLite foreign key support.")
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
