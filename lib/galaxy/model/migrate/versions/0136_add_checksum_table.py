"""
Migration script to add 'dataset_checksum' table.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, TEXT

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

metadata = MetaData()

checksum_table = Table("dataset_checksum", metadata,
                       Column("id", Integer, primary_key=True),
                       Column("dataset_id", Integer, ForeignKey("dataset.id"), index=True),
                       Column("hash_function", TEXT),
                       Column("hash_value", TEXT))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        checksum_table.create()
    except Exception:
        log.exception("Adding `dataset_checksum` table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        checksum_table.drop()
        log.debug("Dropped `dataset_checksum` table.")
    except Exception:
        log.exception("Dropping `dataset_checksum` table failed.")
