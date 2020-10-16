"""
Add dataset_version column to job_to_input_dataset table
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, Integer, MetaData, Table

log = logging.getLogger(__name__)
dataset_version_column = Column("dataset_version", Integer)


def upgrade(migrate_engine):
    print(__doc__)
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    # Add the version column to the job_to_input_dataset table
    try:
        job_to_input_dataset_table = Table("job_to_input_dataset", metadata, autoload=True)
        dataset_version_column.create(job_to_input_dataset_table)
        assert dataset_version_column is job_to_input_dataset_table.c.dataset_version
    except Exception:
        log.exception("Adding column 'dataset_history_id' to job_to_input_dataset table failed.")


def downgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop the job_to_input_dataset table's version column.
    try:
        job_to_input_dataset_table = Table("job_to_input_dataset", metadata, autoload=True)
        dataset_version_column = job_to_input_dataset_table.c.dataset_version
        dataset_version_column.drop()
    except Exception:
        log.exception("Dropping 'dataset_version' column from job_to_input_dataset table failed.")
