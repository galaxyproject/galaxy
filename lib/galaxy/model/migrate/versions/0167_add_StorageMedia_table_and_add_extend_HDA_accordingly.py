"""
Migration script to (a) create a table for StorageMedia and (b) extend the HDA table
linking datasets to storage media.
"""
from __future__ import print_function

import datetime
import logging

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, Numeric, Table, TEXT


now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()

# Tables to add

StorageMediaTable = Table(
    "storage_media", metadata,
    Column("id", Integer, primary_key=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
    Column("usage", Numeric(15, 0), default=0),
    Column("category", TEXT, default="local"),
    Column("path", TEXT),
    Column("deleted", Boolean, index=True, default=False),
    Column("purged", Boolean, index=True, default=False),
    Column("purgeable", Boolean, default=True),
    Column("jobs_directory", TEXT),
    Column("cache_path", TEXT),
    Column("cache_size", Integer))

StorageMediaDatasetAssociation = Table(
    "storage_media_dataset_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("dataset_id", Integer, ForeignKey("dataset.id"), index=True),
    Column("storage_media_id", Integer, ForeignKey("storage_media.id"), index=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    Column("deleted", Boolean, index=True, default=False),
    Column("purged", Boolean, index=True, default=False),
    Column("dataset_path_on_media", TEXT))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # Create StorageMedia table
    try:
        StorageMediaTable.create()
    except Exception as e:
        log.error("Creating storage_media table failed: %s" % str(e))

    # Create StorageMedia Association table.
    try:
        StorageMediaDatasetAssociation.create()
    except Exception as e:
        log.error("Creating storage_media_dataset_association table failed: %s" % str(e))


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop storage_media table
    try:
        StorageMediaTable.drop()
    except Exception as e:
        log.debug("Dropping storage_media table failed: %s" % str(e))

    try:
        StorageMediaDatasetAssociation.drop()
    except Exception as e:
        log.error("Dropping storage_media_dataset_association table failed: %s" % str(e))
