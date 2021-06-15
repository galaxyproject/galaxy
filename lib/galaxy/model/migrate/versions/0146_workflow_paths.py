"""
Migration script for workflow paths.
"""

import logging

from sqlalchemy import (
    Column,
    MetaData,
    TEXT,
)

from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    from_path_column = Column("from_path", TEXT)
    add_column(from_path_column, "stored_workflow", metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine

    drop_column("from_path", "stored_workflow", metadata)
