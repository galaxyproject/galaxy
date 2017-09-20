"""
Migration script to add 'checksum' column to the dataset table.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, MetaData, Table, TEXT

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
checksum_column = Column("checksum", TEXT)


def upgrade(migrate_engine):
    print(__doc__)
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        dataset_table = Table("dataset", metadata, autoload=True)
        checksum_column.create(dataset_table)
        assert checksum_column is dataset_table.c.checksum
    except Exception:
        log.exception("Adding `checksum` column to the `dataset` table failed.")


def downgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        dataset_table = Table("dataset", metadata, autoload=True)
        dataset_table.c.checksum.drop()
        log.debug("Dropped `checksum` column from the `dataset` table.")
    except Exception:
        log.exception("Dropping `checksum` column from the `dataset` table failed.")
