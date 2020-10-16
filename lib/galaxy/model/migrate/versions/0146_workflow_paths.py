"""
Migration script for workflow paths.
"""
from __future__ import print_function

import logging

from sqlalchemy import (
    Column,
    MetaData,
    Table,
    TEXT,
)

log = logging.getLogger(__name__)
metadata = MetaData()

from_path_column = Column("from_path", TEXT, nullable=True)


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    _add_column(from_path_column, "stored_workflow", metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine

    _drop_column("from_path", "stored_workflow", metadata)


def _add_column(column, table_name, metadata, **kwds):
    try:
        table = Table(table_name, metadata, autoload=True)
        column.create(table, **kwds)
    except Exception:
        log.exception("Adding column %s failed.", column)


def _drop_column(column_name, table_name, metadata):
    try:
        table = Table(table_name, metadata, autoload=True)
        getattr(table.c, column_name).drop()
    except Exception:
        log.exception("Dropping column %s failed.", column_name)
