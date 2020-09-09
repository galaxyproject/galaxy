"""
Migration script to add the history_dataset_association_history table.
"""

import datetime
import logging

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Table
)

from galaxy.model.custom_types import (
    MetadataType,
    TrimmedString
)
from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
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

    create_table(HistoryDatasetAssociationHistory_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(HistoryDatasetAssociationHistory_table)
