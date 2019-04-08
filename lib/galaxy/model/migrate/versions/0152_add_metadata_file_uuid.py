"""
Adds `uuid` column to MetadataFile table.
"""

from __future__ import print_function

import logging

from sqlalchemy import Column, MetaData, Table

from galaxy.model.custom_types import UUIDType

log = logging.getLogger(__name__)


def upgrade(migrate_engine):
    print(__doc__)
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    metadata_file_table = Table("metadata_file", metadata, autoload=True)

    try:
        uuid_column = Column('uuid', UUIDType())
        uuid_column.create(metadata_file_table)
        assert uuid_column is metadata_file_table.c.uuid
    except Exception:
        log.exception("Adding column 'uuid' to `MetadataFile` table failed.")


def downgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    metadata_file_table = Table("metadata_file", metadata, autoload=True)

    try:
        column = metadata_file_table.c.uuid
        column.drop()
    except Exception:
        log.exception("Dropping 'uuid' column from `metadata_file` table failed.")
