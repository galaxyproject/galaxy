"""
Migration script to add the request_type_permissions table.
"""

import datetime
import logging

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, Table, TEXT

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()

RequestTypePermissions_table = Table("request_type_permissions", metadata,
                                     Column("id", Integer, primary_key=True),
                                     Column("create_time", DateTime, default=now),
                                     Column("update_time", DateTime, default=now, onupdate=now),
                                     Column("action", TEXT),
                                     Column("request_type_id", Integer, ForeignKey("request_type.id"), nullable=True, index=True),
                                     Column("role_id", Integer, ForeignKey("role.id"), index=True))


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    try:
        RequestTypePermissions_table.create()
    except Exception:
        log.exception("Creating request_type_permissions table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        RequestTypePermissions_table = Table("request_type_permissions", metadata, autoload=True)
        RequestTypePermissions_table.drop()
    except Exception:
        log.exception("Dropping 'request_type_permissions' table failed.")
