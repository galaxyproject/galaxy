"""
Migration script to add slug column for stored workflow.
"""

import logging

from sqlalchemy import (
    Column,
    MetaData,
    Table,
    TEXT
)

from galaxy.model.migrate.versions.util import (
    add_column,
    add_index,
    drop_column
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    StoredWorkflow_table = Table("stored_workflow", metadata, autoload=True)
    c = Column("slug", TEXT)
    add_column(c, StoredWorkflow_table, metadata)
    # Index needs to be added separately because MySQL cannot index a TEXT/BLOB
    # column without specifying mysql_length
    add_index('ix_stored_workflow_slug', StoredWorkflow_table, 'slug')


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('slug', 'stored_workflow', metadata)
