"""
Migration script to add deleted column to API keys
"""

import datetime
import logging

from sqlalchemy import (
    Boolean,
    Column,
    MetaData,
    Table,
)

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()

TABLE_NAME = "api_keys"
COLUMN_NAME = "deleted"


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    deleted_column = Column(COLUMN_NAME, Boolean)
    __add_column(deleted_column, TABLE_NAME, metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    __drop_column(COLUMN_NAME, TABLE_NAME, metadata)


def __add_column(column, table_name, metadata, **kwds):
    try:
        table = Table(table_name, metadata, autoload=True)
        column.create(table, **kwds)
    except Exception:
        log.exception("Adding column %s failed.", column)


def __drop_column(column_name, table_name, metadata):
    try:
        table = Table(table_name, metadata, autoload=True)
        getattr(table.c, column_name).drop()
    except Exception:
        log.exception("Dropping column %s failed.", column_name)
