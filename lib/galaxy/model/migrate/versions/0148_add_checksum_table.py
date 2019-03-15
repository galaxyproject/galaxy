"""
Migration script to add dataset source and hash tables.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, TEXT

from galaxy.model.custom_types import JSONType

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

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
    try:
        dataset_source_table.create()
        dataset_hash_table.create()
        dataset_source_hash_table.create()
    except Exception:
        log.exception("Adding dataset source and hash tables failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        dataset_source_table.drop()
        dataset_hash_table.drop()
        dataset_source_hash_table.drop()
    except Exception:
        log.exception("Dropping dataset source and hash tables failed.")
