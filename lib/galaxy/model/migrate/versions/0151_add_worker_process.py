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

from galaxy.model.migrate.versions.util import create_table, drop_table
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
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(WorkerProcess_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(WorkerProcess_table)
