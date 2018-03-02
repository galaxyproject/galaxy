"""
Add copied_from_job_id column to jobs table
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, Integer, MetaData, Table

log = logging.getLogger(__name__)
copied_from_job_id_column = Column("copied_from_job_id", Integer, nullable=True)


def upgrade(migrate_engine):
    print(__doc__)
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    # Add the copied_from_job_id column to the job table
    try:
        jobs_table = Table("job", metadata, autoload=True)
        copied_from_job_id_column.create(jobs_table)
        assert copied_from_job_id_column is jobs_table.c.copied_from_job_id
    except Exception:
        log.exception("Adding column 'copied_from_job_id_column' to job table failed.")


def downgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop the job table's copied_from_job_id column.
    try:
        jobs_table = Table("job", metadata, autoload=True)
        copied_from_job_id = jobs_table.c.copied_from_job_id
        copied_from_job_id.drop()
    except Exception:
        log.exception("Dropping 'copied_from_job_id_column' column from job table failed.")
