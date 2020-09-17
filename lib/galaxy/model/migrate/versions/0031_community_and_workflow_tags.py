"""
Migration script to (a) add and populate necessary columns for doing community tagging of histories, datasets, and pages and \
(b) add table for doing individual and community tagging of workflows.
"""

import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    Unicode
)

from galaxy.model.migrate.versions.util import (
    add_column,
    create_table,
    drop_column,
    drop_table
)

log = logging.getLogger(__name__)
metadata = MetaData()

StoredWorkflowTagAssociation_table = Table("stored_workflow_tag_association", metadata,
                                           Column("id", Integer, primary_key=True),
                                           Column("stored_workflow_id", Integer, ForeignKey("stored_workflow.id"), index=True),
                                           Column("tag_id", Integer, ForeignKey("tag.id"), index=True),
                                           Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                           Column("user_tname", Unicode(255), index=True),
                                           Column("value", Unicode(255), index=True),
                                           Column("user_value", Unicode(255), index=True))

WorkflowTagAssociation_table = Table("workflow_tag_association", metadata,
                                     Column("id", Integer, primary_key=True),
                                     Column("workflow_id", Integer, ForeignKey("workflow.id"), index=True),
                                     Column("tag_id", Integer, ForeignKey("tag.id"), index=True),
                                     Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                     Column("user_tname", Unicode(255), index=True),
                                     Column("value", Unicode(255), index=True),
                                     Column("user_value", Unicode(255), index=True))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # Create user_id column in history_tag_association table.
    c = Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True)
    add_column(c, 'history_tag_association', metadata, index_name='ix_history_tag_association_user_id')

    # Populate column so that user_id is the id of the user who owns the history (and, up to now, was the only person able to tag the history).
    migrate_engine.execute(
        "UPDATE history_tag_association SET user_id=( SELECT user_id FROM history WHERE history_tag_association.history_id = history.id )")

    # Create user_id column in history_dataset_association_tag_association table.
    c = Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True)
    add_column(c, 'history_dataset_association_tag_association', metadata, index_name='ix_history_dataset_association_tag_association_user_id')

    # Populate column so that user_id is the id of the user who owns the history_dataset_association (and, up to now, was the only person able to tag the page).
    migrate_engine.execute(
        "UPDATE history_dataset_association_tag_association SET user_id=( SELECT history.user_id FROM history, history_dataset_association WHERE history_dataset_association.history_id = history.id AND history_dataset_association.id = history_dataset_association_tag_association.history_dataset_association_id)")

    # Create user_id column in page_tag_association table.
    c = Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True)
    add_column(c, 'page_tag_association', metadata, index_name='ix_page_tag_association_user_id')

    # Populate column so that user_id is the id of the user who owns the page (and, up to now, was the only person able to tag the page).
    migrate_engine.execute(
        "UPDATE page_tag_association SET user_id=( SELECT user_id FROM page WHERE page_tag_association.page_id = page.id )")

    # Create stored_workflow_tag_association table.
    create_table(StoredWorkflowTagAssociation_table)

    # Create workflow_tag_association table.
    create_table(WorkflowTagAssociation_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop workflow_tag_association table.
    drop_table(WorkflowTagAssociation_table)

    # Drop stored_workflow_tag_association table.
    drop_table(StoredWorkflowTagAssociation_table)

    # Drop user_id column from page_tag_association table.
    drop_column('user_id', 'page_tag_association', metadata)

    # Drop user_id column from history_dataset_association_tag_association table.
    drop_column('user_id', 'history_dataset_association_tag_association', metadata)

    # Drop user_id column from history_tag_association table.
    drop_column('user_id', 'history_tag_association', metadata)
