"""
Migration script to create tables for disk quotas.
"""

import datetime
import logging

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, MetaData, String, Table, TEXT

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()

# Tables to add

Quota_table = Table("quota", metadata,
                    Column("id", Integer, primary_key=True),
                    Column("create_time", DateTime, default=now),
                    Column("update_time", DateTime, default=now, onupdate=now),
                    Column("name", String(255), index=True, unique=True),
                    Column("description", TEXT),
                    Column("bytes", BigInteger),
                    Column("operation", String(8)),
                    Column("deleted", Boolean, index=True, default=False))

UserQuotaAssociation_table = Table("user_quota_association", metadata,
                                   Column("id", Integer, primary_key=True),
                                   Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                   Column("quota_id", Integer, ForeignKey("quota.id"), index=True),
                                   Column("create_time", DateTime, default=now),
                                   Column("update_time", DateTime, default=now, onupdate=now))

GroupQuotaAssociation_table = Table("group_quota_association", metadata,
                                    Column("id", Integer, primary_key=True),
                                    Column("group_id", Integer, ForeignKey("galaxy_group.id"), index=True),
                                    Column("quota_id", Integer, ForeignKey("quota.id"), index=True),
                                    Column("create_time", DateTime, default=now),
                                    Column("update_time", DateTime, default=now, onupdate=now))

DefaultQuotaAssociation_table = Table("default_quota_association", metadata,
                                      Column("id", Integer, primary_key=True),
                                      Column("create_time", DateTime, default=now),
                                      Column("update_time", DateTime, default=now, onupdate=now),
                                      Column("type", String(32), index=True, unique=True),
                                      Column("quota_id", Integer, ForeignKey("quota.id"), index=True))


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    # Create quota table
    try:
        Quota_table.create()
    except Exception:
        log.exception("Creating quota table failed.")

    # Create user_quota_association table
    try:
        UserQuotaAssociation_table.create()
    except Exception:
        log.exception("Creating user_quota_association table failed.")

    # Create group_quota_association table
    try:
        GroupQuotaAssociation_table.create()
    except Exception:
        log.exception("Creating group_quota_association table failed.")

    # Create default_quota_association table
    try:
        DefaultQuotaAssociation_table.create()
    except Exception:
        log.exception("Creating default_quota_association table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop default_quota_association table
    try:
        DefaultQuotaAssociation_table.drop()
    except Exception:
        log.exception("Dropping default_quota_association table failed.")

    # Drop group_quota_association table
    try:
        GroupQuotaAssociation_table.drop()
    except Exception:
        log.exception("Dropping group_quota_association table failed.")

    # Drop user_quota_association table
    try:
        UserQuotaAssociation_table.drop()
    except Exception:
        log.exception("Dropping user_quota_association table failed.")

    # Drop quota table
    try:
        Quota_table.drop()
    except Exception:
        log.exception("Dropping quota table failed.")
