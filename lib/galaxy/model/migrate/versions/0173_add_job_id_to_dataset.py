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
    add_index,
    drop_column,
    drop_index,
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    job_id_column = Column('job_id', Integer, ForeignKey('job.id'))
    add_column(job_id_column, 'dataset', metadata)
    add_index('ix_dataset_job_id', 'dataset', 'job_id', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('job_id', 'dataset', metadata)
    drop_index('ix_dataset_job_id', 'dataset', 'job_id', metadata)
