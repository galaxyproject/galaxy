"""
Adds `pid` column to worker_process table.
"""


import logging

from sqlalchemy import (
    Column,
    Integer,
    MetaData
)

from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column
)

log = logging.getLogger(__name__)


def upgrade(migrate_engine):
    print(__doc__)
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    pid_column = Column('pid', Integer)
    add_column(pid_column, 'worker_process', metadata)


def downgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('pid', 'worker_process', metadata)
