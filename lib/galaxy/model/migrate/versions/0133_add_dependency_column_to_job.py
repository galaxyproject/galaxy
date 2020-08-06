"""
Add dependencies column to jobs table
"""

import logging

from sqlalchemy import Column, MetaData, Table

from galaxy.model.custom_types import JSONType

log = logging.getLogger(__name__)
jobs_dependencies_column = Column("dependencies", JSONType, nullable=True)


def upgrade(migrate_engine):
    print(__doc__)
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    # Add the dependencies column to the job table
    try:
        jobs_table = Table("job", metadata, autoload=True)
        jobs_dependencies_column.create(jobs_table)
        assert jobs_dependencies_column is jobs_table.c.dependencies
    except Exception:
        log.exception("Adding column 'dependencies' to job table failed.")


def downgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop the job table's dependencies column.
    try:
        jobs_table = Table("job", metadata, autoload=True)
        jobs_dependencies = jobs_table.c.dependencies
        jobs_dependencies.drop()
    except Exception:
        log.exception("Dropping 'dependencies' column from job table failed.")
