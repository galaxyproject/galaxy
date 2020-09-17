"""
This migration script adds a user actions table to Galaxy.
"""

import datetime
import logging

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, Table, Unicode

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()

# New table to store user actions.
UserAction_table = Table("user_action", metadata,
                         Column("id", Integer, primary_key=True),
                         Column("create_time", DateTime, default=now),
                         Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                         Column("session_id", Integer, ForeignKey("galaxy_session.id"), index=True),
                         Column("action", Unicode(255)),
                         Column("context", Unicode(512)),
                         Column("params", Unicode(1024)))


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    try:
        UserAction_table.create()
    except Exception:
        log.exception("Creating user_action table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        UserAction_table.drop()
    except Exception:
        log.exception("Dropping user_action table failed.")
