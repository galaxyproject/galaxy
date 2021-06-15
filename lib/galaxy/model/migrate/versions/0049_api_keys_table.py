"""
Migration script to add the api_keys table.
"""

import datetime
import logging

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, Table

from galaxy.model.custom_types import TrimmedString

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()

APIKeys_table = Table("api_keys", metadata,
                      Column("id", Integer, primary_key=True),
                      Column("create_time", DateTime, default=now),
                      Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                      Column("key", TrimmedString(32), index=True, unique=True))


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    try:
        APIKeys_table.create()
    except Exception:
        log.exception("Creating api_keys table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    # Load existing tables
    metadata.reflect()
    try:
        APIKeys_table.drop()
    except Exception:
        log.exception("Dropping api_keys table failed.")
