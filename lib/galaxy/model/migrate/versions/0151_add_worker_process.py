"""
Add table for worker processes
"""
from __future__ import print_function

import logging

from sqlalchemy import (
    Column,
    DateTime,
    MetaData,
    Table,
    TEXT,
)

from galaxy.model.orm.now import now

log = logging.getLogger(__name__)
metadata = MetaData()


WorkerProcess_table = Table(
    'worker_process',
    metadata,
    Column('server_name', TEXT, primary_key=True),
    Column("update_time", DateTime, default=now, onupdate=now),
)


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    _create(WorkerProcess_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    _drop(WorkerProcess_table)


def _create(table):
    try:
        table.create()
    except Exception:
        log.exception("Creating %s table failed.", table.name)


def _drop(table):
    try:
        table.drop()
    except Exception:
        log.exception("Dropping %s table failed.", table.name)
