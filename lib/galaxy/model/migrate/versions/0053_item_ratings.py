"""
Migration script to create tables for rating histories, datasets, workflows, pages, and visualizations.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, ForeignKey, Index, Integer, MetaData, Table

log = logging.getLogger(__name__)
metadata = MetaData()

# Rating tables.

HistoryRatingAssociation_table = Table("history_rating_association", metadata,
                                       Column("id", Integer, primary_key=True),
                                       Column("history_id", Integer, ForeignKey("history.id"), index=True),
                                       Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                       Column("rating", Integer, index=True))

HistoryDatasetAssociationRatingAssociation_table = Table("history_dataset_association_rating_association", metadata,
                                                         Column("id", Integer, primary_key=True),
                                                         Column("history_dataset_association_id", Integer, ForeignKey("history_dataset_association.id"), index=True),
                                                         Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                                         Column("rating", Integer, index=True))

StoredWorkflowRatingAssociation_table = Table("stored_workflow_rating_association", metadata,
                                              Column("id", Integer, primary_key=True),
                                              Column("stored_workflow_id", Integer, ForeignKey("stored_workflow.id"), index=True),
                                              Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                              Column("rating", Integer, index=True))

PageRatingAssociation_table = Table("page_rating_association", metadata,
                                    Column("id", Integer, primary_key=True),
                                    Column("page_id", Integer, ForeignKey("page.id"), index=True),
                                    Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                    Column("rating", Integer, index=True))

VisualizationRatingAssociation_table = Table("visualization_rating_association", metadata,
                                             Column("id", Integer, primary_key=True),
                                             Column("visualization_id", Integer, ForeignKey("visualization.id"), index=True),
                                             Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                             Column("rating", Integer, index=True))


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    # Create history_rating_association table.
    try:
        HistoryRatingAssociation_table.create()
    except Exception:
        log.exception("Creating history_rating_association table failed.")

    # Create history_dataset_association_rating_association table.
    try:
        HistoryDatasetAssociationRatingAssociation_table.create()
    except Exception as e:
        # MySQL cannot handle long index names; when we see this error, create the index name manually.
        if migrate_engine.name == 'mysql' and \
                str(e).lower().find("identifier name 'ix_history_dataset_association_rating_association_history_dataset_association_id' is too long"):
            i = Index("ix_hda_rating_association_hda_id", HistoryDatasetAssociationRatingAssociation_table.c.history_dataset_association_id)
            try:
                i.create()
            except Exception:
                log.exception("Adding index 'ix_hda_rating_association_hda_id' to table 'history_dataset_association_rating_association' table failed.")
        else:
            log.exception("Creating history_dataset_association_rating_association table failed.")

    # Create stored_workflow_rating_association table.
    try:
        StoredWorkflowRatingAssociation_table.create()
    except Exception:
        log.exception("Creating stored_workflow_rating_association table failed.")

    # Create page_rating_association table.
    try:
        PageRatingAssociation_table.create()
    except Exception:
        log.exception("Creating page_rating_association table failed.")

    # Create visualization_rating_association table.
    try:
        VisualizationRatingAssociation_table.create()
    except Exception:
        log.exception("Creating visualization_rating_association table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop history_rating_association table.
    try:
        HistoryRatingAssociation_table.drop()
    except Exception:
        log.exception("Dropping history_rating_association table failed.")

    # Drop history_dataset_association_rating_association table.
    try:
        HistoryDatasetAssociationRatingAssociation_table.drop()
    except Exception:
        log.exception("Dropping history_dataset_association_rating_association table failed.")

    # Drop stored_workflow_rating_association table.
    try:
        StoredWorkflowRatingAssociation_table.drop()
    except Exception:
        log.exception("Dropping stored_workflow_rating_association table failed.")

    # Drop page_rating_association table.
    try:
        PageRatingAssociation_table.drop()
    except Exception:
        log.exception("Dropping page_rating_association table failed.")

    # Drop visualization_rating_association table.
    try:
        VisualizationRatingAssociation_table.drop()
    except Exception:
        log.exception("Dropping visualization_rating_association table failed.")
