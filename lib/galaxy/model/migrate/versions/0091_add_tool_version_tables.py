"""
Migration script to create the tool_version and tool_version_association tables and drop the tool_id_guid_map table.
"""

import datetime
import logging
from json import loads

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    TEXT
)

from galaxy.model.custom_types import (
    _sniffnfix_pg9_hex,
    TrimmedString
)
from galaxy.model.migrate.versions.util import (
    localtimestamp,
    nextval
)

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
metadata = MetaData()


ToolVersion_table = Table("tool_version", metadata,
    Column("id", Integer, primary_key=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    Column("tool_id", String(255)),
    Column("tool_shed_repository_id", Integer, ForeignKey("tool_shed_repository.id"), index=True, nullable=True))

ToolVersionAssociation_table = Table("tool_version_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("tool_id", Integer, ForeignKey("tool_version.id"), index=True, nullable=False),
    Column("parent_id", Integer, ForeignKey("tool_version.id"), index=True, nullable=False))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # Create the tables.
    try:
        ToolVersion_table.create()
    except Exception:
        log.exception("Creating tool_version table failed.")
    try:
        ToolVersionAssociation_table.create()
    except Exception:
        log.exception("Creating tool_version_association table failed.")
    # Populate the tool table with tools included in installed tool shed repositories.
    cmd = "SELECT id, metadata FROM tool_shed_repository"
    result = migrate_engine.execute(cmd)
    count = 0
    for row in result:
        if row[1]:
            tool_shed_repository_id = row[0]
            repository_metadata = loads(_sniffnfix_pg9_hex(str(row[1])))
            # Create a new row in the tool table for each tool included in repository.  We will NOT
            # handle tool_version_associaions because we do not have the information we need to do so.
            tools = repository_metadata.get('tools', [])
            for tool_dict in tools:
                cmd = "INSERT INTO tool_version VALUES (%s, %s, %s, '%s', %s)" % \
                    (nextval(migrate_engine, 'tool_version'), localtimestamp(migrate_engine), localtimestamp(migrate_engine), tool_dict['guid'], tool_shed_repository_id)
                migrate_engine.execute(cmd)
                count += 1
    print("Added %d rows to the new tool_version table." % count)
    # Drop the tool_id_guid_map table since the 2 new tables render it unnecessary.
    ToolIdGuidMap_table = Table("tool_id_guid_map", metadata, autoload=True)
    try:
        ToolIdGuidMap_table.drop()
    except Exception:
        log.exception("Dropping tool_id_guid_map table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine

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

    metadata.reflect()
    try:
        ToolVersionAssociation_table.drop()
    except Exception:
        log.exception("Dropping tool_version_association table failed.")
    try:
        ToolVersion_table.drop()
    except Exception:
        log.exception("Dropping tool_version table failed.")
    try:
        ToolIdGuidMap_table.create()
    except Exception:
        log.exception("Creating tool_id_guid_map table failed.")
