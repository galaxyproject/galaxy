"""
Add the ExtendedMetadata and ExtendedMetadataIndex tables
"""

import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    TEXT
)

from galaxy.model.custom_types import JSONType
from galaxy.model.migrate.versions.util import (
    add_column,
    create_table,
    drop_column,
    drop_table
)

log = logging.getLogger(__name__)
metadata = MetaData()

ExtendedMetadata_table = Table("extended_metadata", metadata,
                               Column("id", Integer, primary_key=True),
                               Column("data", JSONType))

ExtendedMetadataIndex_table = Table("extended_metadata_index", metadata,
                                    Column("id", Integer, primary_key=True),
                                    Column("extended_metadata_id", Integer, ForeignKey("extended_metadata.id",
                                                                                       onupdate="CASCADE",
                                                                                       ondelete="CASCADE"),
                                           index=True),
                                    Column("path", String(255)),
                                    Column("value", TEXT))

TABLES = [
    ExtendedMetadata_table,
    ExtendedMetadataIndex_table
]


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in TABLES:
        create_table(table)
    extended_metadata_ldda_col = Column("extended_metadata_id", Integer, ForeignKey("extended_metadata.id"), nullable=True)
    add_column(extended_metadata_ldda_col, 'library_dataset_dataset_association', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # TODO: Dropping a column used in a foreign key fails in MySQL, need to remove the FK first.
    drop_column('extended_metadata_id', 'library_dataset_dataset_association', metadata)
    for table in reversed(TABLES):
        drop_table(table)
