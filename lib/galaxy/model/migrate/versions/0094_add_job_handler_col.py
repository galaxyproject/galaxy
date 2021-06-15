"""
Migration script to add a 'handler' column to the 'job' table.
"""

import logging

from sqlalchemy import Column, MetaData

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import add_column, drop_column

log = logging.getLogger(__name__)
metadata = MetaData()

# Column to add.
handler_col = Column("handler", TrimmedString(255), index=True)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    add_column(handler_col, 'job', metadata, index_name="ix_job_handler")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('handler', 'job', metadata)
