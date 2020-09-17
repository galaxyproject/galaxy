"""
Migration script to add 'ldda_parent_id' column to the implicitly_converted_dataset_association table.
"""

import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData
)

from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    c = Column("ldda_parent_id", Integer, ForeignKey("library_dataset_dataset_association.id"), index=True, nullable=True)
    add_column(c, 'implicitly_converted_dataset_association', metadata, index_name='ix_implicitly_converted_dataset_assoc_ldda_parent_id')


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('ldda_parent_id', 'implicitly_converted_dataset_association', metadata)
