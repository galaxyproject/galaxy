"""
Migration script to create missing indexes.  Adding new columns to existing tables via SQLAlchemy does not create the index, even if the column definition includes index=True.
"""

import logging

from sqlalchemy import MetaData

from galaxy.model.migrate.versions.util import (
    add_index,
    drop_index
)

log = logging.getLogger(__name__)
metadata = MetaData()

indexes = [
    [
        "ix_workflow_invocation_output_dataset_association_workflow_output_id",
        "workflow_invocation_output_dataset_association",
        "workflow_output_id"
    ],
    [
        "ix_workflow_invocation_output_dataset_association_workflow_step_id",
        "workflow_invocation_output_dataset_association",
        "workflow_step_id"
    ],
    [
        "ix_workflow_invocation_output_dataset_collection_association_workflow_output_id",
        "workflow_invocation_output_dataset_collection_association",
        "workflow_output_id"
    ],
    [
        "ix_workflow_invocation_output_dataset_collection_association_workflow_step_id",
        "workflow_invocation_output_dataset_collection_association",
        "workflow_step_id"
    ],
    [
        "ix_workflow_invocation_step_output_dataset_collection_association_workflow_step_id",
        "workflow_invocation_step_output_dataset_collection_association",
        "workflow_step_id"
    ],
]


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    for ix, table, col in indexes:
        add_index(ix, table, col, metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    for ix, table, col in indexes:
        drop_index(ix, table, col, metadata)
