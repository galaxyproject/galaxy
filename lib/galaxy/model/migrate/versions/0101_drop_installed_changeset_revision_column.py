"""
Migration script to drop the installed_changeset_revision column from the tool_dependency table.
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

    drop_column('installed_changeset_revision', 'tool_dependency', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    c = Column("installed_changeset_revision", TrimmedString(255))
    add_column(c, "tool_dependency", metadata)
