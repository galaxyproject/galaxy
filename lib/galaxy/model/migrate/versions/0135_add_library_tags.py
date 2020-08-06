"""
This migration script adds support for storing tags in the context of a dataset in a library
"""

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import TrimmedString

log = logging.getLogger(__name__)
metadata = MetaData()


LibraryDatasetDatasetAssociationTagAssociation_table = Table(
    "library_dataset_dataset_association_tag_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("library_dataset_dataset_association_id", Integer, ForeignKey("library_dataset_dataset_association.id"), index=True),
    Column("tag_id", Integer, ForeignKey("tag.id"), index=True),
    Column("user_tname", TrimmedString(255), index=True),
    Column("value", TrimmedString(255), index=True),
    Column("user_value", TrimmedString(255), index=True),
    Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True)
)


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    try:
        LibraryDatasetDatasetAssociationTagAssociation_table.create()
    except Exception:
        log.exception("Creating library_dataset_association_tag_association table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        LibraryDatasetDatasetAssociationTagAssociation_table.drop()
    except Exception:
        log.exception("Dropping library_dataset_association_tag_association table failed.")
