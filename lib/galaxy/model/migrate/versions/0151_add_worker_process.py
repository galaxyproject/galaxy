"""
Add table for worker processes
"""

import logging

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)

from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)
from galaxy.model.orm.now import now

log = logging.getLogger(__name__)
metadata = MetaData()


WorkerProcess_table = Table(
    'worker_process',
    metadata,
    Column("id", Integer, primary_key=True),
    Column("server_name", String(255), index=True),
    Column("hostname", String(255)),
    Column("update_time", DateTime, default=now, onupdate=now),
    UniqueConstraint('server_name', 'hostname'),
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
