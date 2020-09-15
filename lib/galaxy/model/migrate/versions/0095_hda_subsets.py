"""
Migration script to create table for tracking history_dataset_association subsets.
"""

import logging

from sqlalchemy import Column, ForeignKey, Index, Integer, MetaData, Table, Unicode

log = logging.getLogger(__name__)
metadata = MetaData()

# Table to add.

HistoryDatasetAssociationSubset_table = Table("history_dataset_association_subset", metadata,
                                              Column("id", Integer, primary_key=True),
                                              Column("history_dataset_association_id", Integer, ForeignKey("history_dataset_association.id")),
                                              Column("history_dataset_association_subset_id", Integer, ForeignKey("history_dataset_association.id")),
                                              Column("location", Unicode(255), index=True))


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    # Create history_dataset_association_subset.
    try:
        HistoryDatasetAssociationSubset_table.create()
    except Exception:
        log.exception("Creating history_dataset_association_subset table failed.")

    # Manually create indexes because they are too long for MySQL databases.
    i1 = Index("ix_hda_id", HistoryDatasetAssociationSubset_table.c.history_dataset_association_id)
    i2 = Index("ix_hda_subset_id", HistoryDatasetAssociationSubset_table.c.history_dataset_association_subset_id)
    try:
        i1.create()
        i2.create()
    except Exception:
        log.exception("Adding indices to table 'history_dataset_association_subset' table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop history_dataset_association_subset table.
    try:
        HistoryDatasetAssociationSubset_table.drop()
    except Exception:
        log.exception("Dropping history_dataset_association_subset table failed.")
