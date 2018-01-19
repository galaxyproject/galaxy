"""
Add version column to  history_dataset_association table
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, Integer, MetaData, Table

log = logging.getLogger(__name__)
version_column = Column("version", Integer, default=1)


def upgrade(migrate_engine):
    print(__doc__)
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    # Add the version column to the history_dataset_association table
    try:
        hda_table = Table("history_dataset_association", metadata, autoload=True)
        version_column.create(hda_table)
        assert version_column is hda_table.c.version
    except Exception:
        log.exception("Adding column 'copied_from_job_id_column' to job table failed.")


def downgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop the history_dataset_association table's version column.
    try:
        hda_table = Table("history_dataset_association", metadata, autoload=True)
        version_column = hda_table.c.version
        version_column.drop()
    except Exception:
        log.exception("Dropping 'copied_from_job_id_column' column from job table failed.")
