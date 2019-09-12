"""
Migration script to create tables for rating histories, datasets, workflows, pages, and visualizations.
"""
from __future__ import print_function

import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Table
)

from galaxy.model.migrate.versions.util import (
    add_index,
    create_table,
    drop_table
)

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
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(HistoryRatingAssociation_table)

    # Create history_dataset_association_rating_association table.
    try:
        HistoryDatasetAssociationRatingAssociation_table.create()
    except Exception as e:
        # MySQL cannot handle long index names; when we see this error, create the index name manually.
        if migrate_engine.name == 'mysql' and \
                str(e).lower().find("identifier name 'ix_history_dataset_association_rating_association_history_dataset_association_id' is too long"):
            add_index('ix_hda_rating_association_hda_id', HistoryDatasetAssociationRatingAssociation_table, 'history_dataset_association_id')
        else:
            log.exception("Creating history_dataset_association_rating_association table failed.")

    create_table(StoredWorkflowRatingAssociation_table)
    create_table(PageRatingAssociation_table)
    create_table(VisualizationRatingAssociation_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(VisualizationRatingAssociation_table)
    drop_table(PageRatingAssociation_table)
    drop_table(StoredWorkflowRatingAssociation_table)
    drop_table(HistoryDatasetAssociationRatingAssociation_table)
    drop_table(HistoryRatingAssociation_table)
