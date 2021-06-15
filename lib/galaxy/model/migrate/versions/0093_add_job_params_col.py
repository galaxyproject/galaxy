"""
Migration script to add a 'params' column to the 'job' table.
"""

import logging

from sqlalchemy import Column, MetaData, Table

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import TrimmedString

log = logging.getLogger(__name__)
metadata = MetaData()

# Column to add.
params_col = Column("params", TrimmedString(255), index=True)


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    # Add column to Job table.
    try:
        Job_table = Table("job", metadata, autoload=True)
        params_col.create(Job_table, index_name="ix_job_params")
        assert params_col is Job_table.c.params

    except Exception:
        log.exception("Adding column 'params' to job table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop column from Job table.
    try:
        Job_table = Table("job", metadata, autoload=True)
        params_col = Job_table.c.params
        params_col.drop()
    except Exception:
        log.exception("Dropping column 'params' from job table failed.")
