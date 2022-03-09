"""
Migration script for adding source_metadata column to workflow table.
"""

import logging

from sqlalchemy import (
    Column,
    MetaData,
)

from galaxy.model.custom_types import JSONType
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

    source_metadata_column = Column("source_metadata", JSONType)
    add_column(source_metadata_column, "workflow", metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column("source_metadata", "workflow", metadata)
