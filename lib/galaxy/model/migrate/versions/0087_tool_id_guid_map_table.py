"""
Migration script to create the tool_id_guid_map table.
"""

import datetime
import logging

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    String,
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

ToolIdGuidMap_table = Table(
    "tool_id_guid_map", metadata,
    Column("id", Integer, primary_key=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    Column("tool_id", String(255)),
    Column("tool_version", TEXT),
    Column("tool_shed", TrimmedString(255)),
    Column("repository_owner", TrimmedString(255)),
    Column("repository_name", TrimmedString(255)),
    Column("guid", TEXT),
    Index('ix_tool_id_guid_map_guid', 'guid', unique=True, mysql_length=200),
)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(ToolIdGuidMap_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(ToolIdGuidMap_table)
