"""
Rework dataset validation in database.
"""

import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    TEXT,
)

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import add_column, create_table, drop_column, drop_table

log = logging.getLogger(__name__)
metadata = MetaData()

validation_error_table = Table("validation_error", metadata,
    Column("id", Integer, primary_key=True),
    Column("dataset_id", Integer, ForeignKey("history_dataset_association.id"), index=True),
    Column("message", TrimmedString(255)),
    Column("err_type", TrimmedString(64)),
    Column("attributes", TEXT))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(validation_error_table)

    history_dataset_association_table = Table("history_dataset_association", metadata, autoload=True)
    library_dataset_dataset_association_table = Table("library_dataset_dataset_association", metadata, autoload=True)
    for dataset_instance_table in [history_dataset_association_table, library_dataset_dataset_association_table]:
        validated_state_column = Column('validated_state', TrimmedString(64), default='unknown', server_default="unknown", nullable=False)
        add_column(validated_state_column, dataset_instance_table, metadata)

        validated_state_message_column = Column('validated_state_message', TEXT)
        add_column(validated_state_message_column, dataset_instance_table, metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(validation_error_table)

    history_dataset_association_table = Table("history_dataset_association", metadata, autoload=True)
    library_dataset_dataset_association_table = Table("library_dataset_dataset_association", metadata, autoload=True)
    for dataset_instance_table in [history_dataset_association_table, library_dataset_dataset_association_table]:
        drop_column('validated_state', dataset_instance_table, metadata)
        drop_column('validated_state_message', dataset_instance_table, metadata)
