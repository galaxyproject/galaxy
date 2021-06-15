"""
Migration script updating collections tables for output collections.
"""

import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    TEXT,
    Unicode
)

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import (
    add_column,
    create_table,
    drop_column,
    drop_table
)

log = logging.getLogger(__name__)
metadata = MetaData()

JobToImplicitOutputDatasetCollectionAssociation_table = Table(
    "job_to_implicit_output_dataset_collection", metadata,
    Column("id", Integer, primary_key=True),
    Column("job_id", Integer, ForeignKey("job.id"), index=True),
    Column("dataset_collection_id", Integer, ForeignKey("dataset_collection.id"), index=True),
    Column("name", Unicode(255))
)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(JobToImplicitOutputDatasetCollectionAssociation_table)

    dataset_collection_table = Table("dataset_collection", metadata, autoload=True)
    # need server_default because column in non-null
    populated_state_column = Column('populated_state', TrimmedString(64), default='ok', server_default="ok", nullable=False)
    add_column(populated_state_column, dataset_collection_table, metadata)

    populated_message_column = Column('populated_state_message', TEXT, nullable=True)
    add_column(populated_message_column, dataset_collection_table, metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(JobToImplicitOutputDatasetCollectionAssociation_table)

    dataset_collection_table = Table("dataset_collection", metadata, autoload=True)
    drop_column('populated_state', dataset_collection_table)
    drop_column('populated_state_message', dataset_collection_table)
