"""
Migration script to add dataset source and hash tables.
"""

import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    TEXT
)

from galaxy.model.custom_types import JSONType
from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)

log = logging.getLogger(__name__)
metadata = MetaData()

dataset_source_table = Table(
    "dataset_source", metadata,
    Column("id", Integer, primary_key=True),
    Column("dataset_id", Integer, ForeignKey("dataset.id"), index=True),
    Column("source_uri", TEXT),
    Column("extra_files_path", TEXT),
    Column("transform", JSONType)
)

dataset_hash_table = Table(
    "dataset_hash", metadata,
    Column("id", Integer, primary_key=True),
    Column("dataset_id", Integer, ForeignKey("dataset.id"), index=True),
    Column("hash_function", TEXT),
    Column("hash_value", TEXT),
    Column("extra_files_path", TEXT),
)

dataset_source_hash_table = Table(
    "dataset_source_hash", metadata,
    Column("id", Integer, primary_key=True),
    Column("dataset_source_id", Integer, ForeignKey("dataset_source.id"), index=True),
    Column("hash_function", TEXT),
    Column("hash_value", TEXT)
)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    create_table(dataset_source_table)
    create_table(dataset_hash_table)
    create_table(dataset_source_hash_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    drop_table(dataset_source_hash_table)
    drop_table(dataset_hash_table)
    drop_table(dataset_source_table)
