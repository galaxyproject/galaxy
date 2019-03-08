"""
Migration script to add a new tables for RealTimeTools.
"""
from __future__ import print_function

import logging

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, String, Table, TEXT

from galaxy.model.custom_types import JSONType
from galaxy.model.orm.now import now

log = logging.getLogger(__name__)
metadata = MetaData()

realtime_tool = Table(
    "realtime_tool", metadata,
    Column("id", Integer, primary_key=True),
    Column("job_id", Integer, ForeignKey("job.id"), index=True),
    Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
    Column("session_id", Integer, ForeignKey("galaxy_session.id"), index=True),
    Column("dataset_id", Integer, ForeignKey("history_dataset_association.id"), index=True),
    Column("created_time", DateTime, default=now),
    Column("modified_time", DateTime, default=now, onupdate=now))


realtime_tool_entry_point = Table(
    "realtime_tool_entry_point", metadata,
    Column("id", Integer, primary_key=True),
    Column("realtime_id", Integer, ForeignKey("realtime_tool.id"), index=True),
    Column("name", TEXT),
    Column("token", TEXT),
    Column("tool_port", Integer),
    Column("host", TEXT),
    Column("port", Integer),
    Column("protocol", TEXT),
    Column("configured", Boolean, default=False),
    Column("entry_url", TEXT),
    Column("created_time", DateTime, default=now),
    Column("modified_time", DateTime, default=now, onupdate=now))

job_container_association = Table(
    "job_container_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("job_id", Integer, ForeignKey("job.id"), index=True),
    Column("container_type", TEXT),
    Column("container_name", TEXT),
    Column("container_info", JSONType, nullable=True),
    Column("created_time", DateTime, default=now),
    Column("modified_time", DateTime, default=now, onupdate=now))

def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        realtime_tool.create()
    except Exception:
        log.exception("Failed to create realtime_tool table")

    try:
        job_container_association.create()
    except Exception:
        log.exception("Failed to create job_container_association table")

    try:
        realtime_tool_entry_point.create()
    except Exception:
        log.exception("Failed to create realtime_tool_entry_point table")

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        realtime_tool.drop()
    except Exception:
        log.exception("Failed to drop realtime_tool table")

    try:
        job_container_association.drop()
    except Exception:
        log.exception("Failed to drop job_container_association table")

    try:
        realtime_tool_entry_point.drop()
    except Exception:
        log.exception("Failed to drop realtime_tool_entry_point table")
