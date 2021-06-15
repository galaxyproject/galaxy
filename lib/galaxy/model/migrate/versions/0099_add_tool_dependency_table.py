"""
Migration script to add the tool_dependency table.
"""

import datetime
import logging

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Table
)

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
metadata = MetaData()

# New table to store information about cloned tool shed repositories.
ToolDependency_table = Table("tool_dependency", metadata,
                             Column("id", Integer, primary_key=True),
                             Column("create_time", DateTime, default=now),
                             Column("update_time", DateTime, default=now, onupdate=now),
                             Column("tool_shed_repository_id", Integer, ForeignKey("tool_shed_repository.id"), index=True, nullable=False),
                             Column("installed_changeset_revision", TrimmedString(255)),
                             Column("name", TrimmedString(255)),
                             Column("version", TrimmedString(40)),
                             Column("type", TrimmedString(40)),
                             Column("uninstalled", Boolean, default=False))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(ToolDependency_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(ToolDependency_table)
