"""
Migration script to (a) create tables for annotating objects and (b) create tags for workflow steps.
"""

import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Table,
    TEXT,
    Unicode
)

from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)

log = logging.getLogger(__name__)
metadata = MetaData()

# Annotation tables.

HistoryAnnotationAssociation_table = Table(
    "history_annotation_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("history_id", Integer, ForeignKey("history.id"), index=True),
    Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
    Column("annotation", TEXT),
    Index("ix_history_anno_assoc_annotation", 'annotation', mysql_length=200),
)

HistoryDatasetAssociationAnnotationAssociation_table = Table(
    "history_dataset_association_annotation_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("history_dataset_association_id", Integer,
        ForeignKey("history_dataset_association.id"), index=True),
    Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
    Column("annotation", TEXT),
    Index("ix_history_dataset_anno_assoc_annotation", 'annotation', mysql_length=200),
)

StoredWorkflowAnnotationAssociation_table = Table(
    "stored_workflow_annotation_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("stored_workflow_id", Integer, ForeignKey("stored_workflow.id"), index=True),
    Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
    Column("annotation", TEXT),
    Index("ix_stored_workflow_ann_assoc_annotation", 'annotation', mysql_length=200),
)

WorkflowStepAnnotationAssociation_table = Table(
    "workflow_step_annotation_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("workflow_step_id", Integer, ForeignKey("workflow_step.id"), index=True),
    Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
    Column("annotation", TEXT),
    Index("ix_workflow_step_ann_assoc_annotation", 'annotation', mysql_length=200),
)

# Tagging tables.

WorkflowStepTagAssociation_table = Table("workflow_step_tag_association", metadata,
                                         Column("id", Integer, primary_key=True),
                                         Column("workflow_step_id", Integer, ForeignKey("workflow_step.id"), index=True),
                                         Column("tag_id", Integer, ForeignKey("tag.id"), index=True),
                                         Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                         Column("user_tname", Unicode(255), index=True),
                                         Column("value", Unicode(255), index=True),
                                         Column("user_value", Unicode(255), index=True))

TABLES = [
    HistoryAnnotationAssociation_table,
    HistoryDatasetAssociationAnnotationAssociation_table,
    StoredWorkflowAnnotationAssociation_table,
    WorkflowStepAnnotationAssociation_table,
    WorkflowStepTagAssociation_table
]


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in TABLES:
        create_table(table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in TABLES:
        drop_table(table)
