"""
Migration script to add the ctx_rev column to the tool_shed_repository table.
"""

import logging

from sqlalchemy import (
    Column,
    MetaData
)

from galaxy.model.custom_types import TrimmedString
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

    col = Column("ctx_rev", TrimmedString(10))
    add_column(col, 'tool_shed_repository', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('ctx_rev', 'tool_shed_repository', metadata)
