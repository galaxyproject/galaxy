"""
Migration script to add new tables for InteractiveTools.
"""

import logging

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, Table, TEXT

from galaxy.model.custom_types import JSONType
from galaxy.model.orm.now import now

log = logging.getLogger(__name__)
metadata = MetaData()

interactivetool_entry_point = Table(
    "interactivetool_entry_point", metadata,
    Column("id", Integer, primary_key=True),
    Column("job_id", Integer, ForeignKey("job.id"), index=True),
    Column("name", TEXT),
    Column("token", TEXT),
    Column("tool_port", Integer),
    Column("host", TEXT),
    Column("port", Integer),
    Column("protocol", TEXT),
    Column("entry_url", TEXT),
    Column("info", JSONType, nullable=True),
    Column("configured", Boolean, default=False),
    Column("deleted", Boolean, default=False),
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
        job_container_association.create()
    except Exception:
        log.exception("Failed to create job_container_association table")

    try:
        interactivetool_entry_point.create()
    except Exception:
        log.exception("Failed to create interactivetool_entry_point table")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        job_container_association.drop()
    except Exception:
        log.exception("Failed to drop job_container_association table")

    try:
        interactivetool_entry_point.drop()
    except Exception:
        log.exception("Failed to drop interactivetool_entry_point table")
