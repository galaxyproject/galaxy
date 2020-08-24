"""
This migration script provides support for (a) ordering tags by recency and
(b) tagging pages. This script deletes all existing tags.
"""

import logging

from sqlalchemy import Column, ForeignKey, Index, Integer, MetaData, Table
from sqlalchemy.exc import OperationalError

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import TrimmedString

log = logging.getLogger(__name__)
metadata = MetaData()

HistoryTagAssociation_table = Table("history_tag_association", metadata,
                                    Column("id", Integer, primary_key=True),
                                    Column("history_id", Integer, ForeignKey("history.id"), index=True),
                                    Column("tag_id", Integer, ForeignKey("tag.id"), index=True),
                                    Column("user_tname", TrimmedString(255), index=True),
                                    Column("value", TrimmedString(255), index=True),
                                    Column("user_value", TrimmedString(255), index=True))

DatasetTagAssociation_table = Table("dataset_tag_association", metadata,
                                    Column("id", Integer, primary_key=True),
                                    Column("dataset_id", Integer, ForeignKey("dataset.id"), index=True),
                                    Column("tag_id", Integer, ForeignKey("tag.id"), index=True),
                                    Column("user_tname", TrimmedString(255), index=True),
                                    Column("value", TrimmedString(255), index=True),
                                    Column("user_value", TrimmedString(255), index=True))

HistoryDatasetAssociationTagAssociation_table = Table("history_dataset_association_tag_association", metadata,
                                                      Column("id", Integer, primary_key=True),
                                                      Column("history_dataset_association_id", Integer, ForeignKey("history_dataset_association.id"), index=True),
                                                      Column("tag_id", Integer, ForeignKey("tag.id"), index=True),
                                                      Column("user_tname", TrimmedString(255), index=True),
                                                      Column("value", TrimmedString(255), index=True),
                                                      Column("user_value", TrimmedString(255), index=True))

PageTagAssociation_table = Table("page_tag_association", metadata,
                                 Column("id", Integer, primary_key=True),
                                 Column("page_id", Integer, ForeignKey("page.id"), index=True),
                                 Column("tag_id", Integer, ForeignKey("tag.id"), index=True),
                                 Column("user_tname", TrimmedString(255), index=True),
                                 Column("value", TrimmedString(255), index=True),
                                 Column("user_value", TrimmedString(255), index=True))


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    #
    # Recreate tables.
    #
    try:
        HistoryTagAssociation_table.drop()
        HistoryTagAssociation_table.create()
    except Exception:
        log.exception("Recreating history_tag_association table failed.")

    try:
        DatasetTagAssociation_table.drop()
        DatasetTagAssociation_table.create()
    except Exception:
        log.exception("Recreating dataset_tag_association table failed.")

    try:
        HistoryDatasetAssociationTagAssociation_table.drop()
        HistoryDatasetAssociationTagAssociation_table.create()
    except OperationalError as e:
        # Handle error that results from and index name that is too long; this occurs
        # in MySQL.
        if str(e).find("CREATE INDEX") != -1:
            # Manually create index.
            i = Index("ix_hda_ta_history_dataset_association_id", HistoryDatasetAssociationTagAssociation_table.c.history_dataset_association_id)
            try:
                i.create()
            except Exception:
                log.exception("Adding index 'ix_hda_ta_history_dataset_association_id' to table 'history_dataset_association_tag_association' table failed.")
    except Exception:
        log.exception("Recreating history_dataset_association_tag_association table failed.")

    # Create page_tag_association table.
    try:
        PageTagAssociation_table.create()
    except Exception:
        log.exception("Creating page_tag_association table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # No need to downgrade other tagging tables. They work fine with verision 16 code.

    # Drop page_tag_association table.
    try:
        PageTagAssociation_table.drop()
    except Exception:
        log.exception("Dropping page_tag_association table failed.")
