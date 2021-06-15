"""
Migration script to create table for storing tool tag associations.
"""

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table

from galaxy.model.custom_types import TrimmedString

log = logging.getLogger(__name__)
metadata = MetaData()

# Table to add

ToolTagAssociation_table = Table("tool_tag_association", metadata,
                                 Column("id", Integer, primary_key=True),
                                 Column("tool_id", TrimmedString(255), index=True),
                                 Column("tag_id", Integer, ForeignKey("tag.id"), index=True),
                                 Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                 Column("user_tname", TrimmedString(255), index=True),
                                 Column("value", TrimmedString(255), index=True),
                                 Column("user_value", TrimmedString(255), index=True))


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    # Create tool_tag_association table
    try:
        ToolTagAssociation_table.create()
    except Exception:
        log.exception("Creating tool_tag_association table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop tool_tag_association table
    try:
        ToolTagAssociation_table.drop()
    except Exception:
        log.exception("Dropping tool_tag_association table failed.")
