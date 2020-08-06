"""
Migration script to create table for storing deferred job and managed transfer
information.
"""

import datetime
import logging

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table

from galaxy.model.custom_types import JSONType

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()

# Table to add

DeferredJob_table = Table("deferred_job", metadata,
                          Column("id", Integer, primary_key=True),
                          Column("create_time", DateTime, default=now),
                          Column("update_time", DateTime, default=now, onupdate=now),
                          Column("state", String(64), index=True),
                          Column("plugin", String(128), index=True),
                          Column("params", JSONType))

TransferJob_table = Table("transfer_job", metadata,
                          Column("id", Integer, primary_key=True),
                          Column("create_time", DateTime, default=now),
                          Column("update_time", DateTime, default=now, onupdate=now),
                          Column("state", String(64), index=True),
                          Column("path", String(1024)),
                          Column("params", JSONType))


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    # Create deferred_job table
    try:
        DeferredJob_table.create()
    except Exception:
        log.exception("Creating deferred_job table failed.")

    # Create transfer_job table
    try:
        TransferJob_table.create()
    except Exception:
        log.exception("Creating transfer_job table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop deferred_job table
    try:
        DeferredJob_table.drop()
    except Exception:
        log.exception("Dropping deferred_job table failed.")

    # Drop transfer_job table
    try:
        TransferJob_table.drop()
    except Exception:
        log.exception("Dropping transfer_job table failed.")
