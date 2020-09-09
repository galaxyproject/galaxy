"""
Migration script to add the tool_shed_repository table.
"""

import datetime
import logging

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    Table,
    TEXT
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
ToolShedRepository_table = Table("tool_shed_repository", metadata,
                                 Column("id", Integer, primary_key=True),
                                 Column("create_time", DateTime, default=now),
                                 Column("update_time", DateTime, default=now, onupdate=now),
                                 Column("tool_shed", TrimmedString(255), index=True),
                                 Column("name", TrimmedString(255), index=True),
                                 Column("description", TEXT),
                                 Column("owner", TrimmedString(255), index=True),
                                 Column("changeset_revision", TrimmedString(255), index=True),
                                 Column("deleted", Boolean, index=True, default=False))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(ToolShedRepository_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(ToolShedRepository_table)
