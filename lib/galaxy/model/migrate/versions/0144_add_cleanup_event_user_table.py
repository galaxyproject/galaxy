"""
Migration script to add the cleanup_event_user_association table.
"""
from __future__ import print_function

import datetime
import logging

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, Table

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

metadata = MetaData()

# New table to log cleanup events
CleanupEventUserAssociation_table = Table(
    "cleanup_event_user_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("create_time", DateTime, default=now),
    Column("cleanup_event_id", Integer, ForeignKey("cleanup_event.id"), index=True, nullable=True),
    Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        CleanupEventUserAssociation_table.create()
        log.debug("Created cleanup_event_user_association table")
    except Exception:
        log.exception("Creating cleanup_event_user_association table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        CleanupEventUserAssociation_table.drop()
        log.debug("Dropped cleanup_event_user_association table")
    except Exception:
        log.exception("Dropping cleanup_event_user_association table failed.")
