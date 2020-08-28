"""
Migration script to add a 'hidden' column to the 'StoredWorkflow' table.
"""

import logging

from sqlalchemy import Boolean, Column, MetaData

from galaxy.model.migrate.versions.util import add_column, drop_column

log = logging.getLogger(__name__)
metadata = MetaData()

# Column to add.
hidden_col = Column("hidden", Boolean, default=False)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    add_column(hidden_col, 'stored_workflow', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('hidden', 'stored_workflow', metadata)
