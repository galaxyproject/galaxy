"""
Migration script to add the library_dataset_collection table.
"""

import datetime
import logging

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Table
)

from galaxy.model.custom_types import (
    TrimmedString
)
from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
metadata = MetaData()

LibraryDatasetCollection_table = Table(
    "library_dataset_collection", metadata,
    Column("id", Integer, primary_key=True),
    Column("library_dataset_collection_association_id", Integer,
        ForeignKey(
            "library_dataset_collection_association.id",
            use_alter=True,
            name="library_dataset_collection_association_id_fk",
        ),
        nullable=True, index=True),
    Column("folder_id", Integer, ForeignKey("library_folder.id"), index=True),
    Column("order_id", Integer),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    Column("name", TrimmedString(255), key="_name", index=True),
    Column("deleted", Boolean, index=True, default=False),
    Column("purged", Boolean, index=True, default=False))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(LibraryDatasetCollection_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(LibraryDatasetCollection_table)
