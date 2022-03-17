"""
Migration script for adding job_id column to dataset table.
"""

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

    job_id_column = Column('job_id', Integer, ForeignKey('job.id'), index=True)
    add_column(job_id_column, 'dataset', metadata, index_name='ix_dataset_job_id')


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('job_id', 'dataset', metadata)
