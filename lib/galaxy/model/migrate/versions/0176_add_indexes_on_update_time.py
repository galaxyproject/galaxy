"""
Migration script to add indexes on update_time columns that are frequently used in ORDER BY clauses.
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
        "ix_history_dataset_association_update_time",
        "history_dataset_association",
        "update_time"
    ],
    [
        "ix_library_dataset_dataset_association_update_time",
        "library_dataset_dataset_association",
        "update_time"
    ],
    [
        "ix_job_update_time",
        "job",
        "update_time"
    ],
    [
        "ix_history_dataset_collection_association_update_time",
        "history_dataset_collection_association",
        "update_time"
    ],
    [
        "ix_workflow_invocation_update_time",
        "workflow_invocation",
        "update_time"
    ],
    [
        "ix_stored_workflow_update_time",
        "stored_workflow",
        "update_time"
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
