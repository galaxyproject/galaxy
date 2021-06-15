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
        "ix_galaxy_user_activation_token",
        "galaxy_user",
        "activation_token"
    ],
    [
        "ix_workflow_step_dynamic_tool_id",
        "workflow_step",
        "dynamic_tool_id"
    ],
    [
        "ix_history_dataset_association_version",
        "history_dataset_association",
        "version"
    ],
    [
        "ix_workflow_invocation_scheduler",
        "workflow_invocation",
        "scheduler"
    ],
    [
        "ix_page_slug",
        "page",
        "slug"
    ],
    [
        "ix_workflow_invocation_state",
        "workflow_invocation",
        "state"
    ],
    [
        "ix_history_dataset_collection_association_implicit_collection_jobs_id",
        "history_dataset_collection_association",
        "implicit_collection_jobs_id"
    ],
    [
        "ix_workflow_step_subworkflow_id",
        "workflow_step",
        "subworkflow_id"
    ],
    [
        "ix_dynamic_tool_update_time",
        "dynamic_tool",
        "update_time"
    ],
    [
        "ix_library_dataset_dataset_association_extended_metadata_id",
        "library_dataset_dataset_association",
        "extended_metadata_id"
    ],
    [
        "ix_workflow_invocation_step_implicit_collection_jobs_id",
        "workflow_invocation_step",
        "implicit_collection_jobs_id"
    ],
    [
        "ix_workflow_invocation_step_state",
        "workflow_invocation_step",
        "state"
    ],
    [
        "ix_workflow_invocation_history_id",
        "workflow_invocation",
        "history_id"
    ],
    [
        "ix_workflow_parent_workflow_id",
        "workflow",
        "parent_workflow_id"
    ],
    [
        "ix_metadata_file_uuid",
        "metadata_file",
        "uuid"
    ],
    [
        "ix_history_dataset_collection_association_job_id",
        "history_dataset_collection_association",
        "job_id"
    ],
    [
        "ix_galaxy_user_active",
        "galaxy_user",
        "active"
    ],
    [
        "ix_job_dynamic_tool_id",
        "job",
        "dynamic_tool_id"
    ],
    [
        "ix_history_dataset_association_extended_metadata_id",
        "history_dataset_association",
        "extended_metadata_id"
    ]
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
