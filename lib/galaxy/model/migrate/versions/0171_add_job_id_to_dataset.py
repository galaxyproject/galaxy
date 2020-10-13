"""
Migration script for adding job_id column to dataset table.
"""
from __future__ import print_function

import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
)

from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column,
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    job_id_column = Column('job_id', Integer, ForeignKey('job.id'))
    add_column(job_id_column, 'dataset', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('job_id', 'dataset', metadata)
