"""
Migration script to add the history_dataset_association_history table.
"""
from __future__ import print_function

import datetime
import logging

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, Table

from galaxy.model.custom_types import MetadataType, TrimmedString

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
metadata = MetaData()

HistoryDatasetAssociationHistory_table = Table(
    "history_dataset_association_history", metadata,
    Column("id", Integer, primary_key=True),
    Column("history_dataset_association_id", Integer, ForeignKey("history_dataset_association.id"), index=True),
    Column("update_time", DateTime, default=now),
    Column("version", Integer, index=True),
    Column("name", TrimmedString(255)),
    Column("extension", TrimmedString(64)),
    Column("metadata", MetadataType(), key='_metadata'),
    Column("extended_metadata_id", Integer, ForeignKey("extended_metadata.id"), index=True),
)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        HistoryDatasetAssociationHistory_table.create()
        log.debug("Created history_dataset_association_history table")
    except Exception:
        log.exception("Creating history_dataset_association_history table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        HistoryDatasetAssociationHistory_table.drop()
        log.debug("Dropped history_dataset_association_history table")
    except Exception:
        log.exception("Dropping history_dataset_association_history table failed.")
