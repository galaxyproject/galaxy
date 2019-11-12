"""
Adds `pid` column to worker_process table.
"""

from __future__ import print_function

import logging

from sqlalchemy import (
    Column,
    MetaData
)

from galaxy.model.custom_types import UUIDType
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

    pid_column = Column('pid', int)
    add_column(pid_column, 'worker_process', metadata)


def downgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('pid', 'worker_process', metadata)
