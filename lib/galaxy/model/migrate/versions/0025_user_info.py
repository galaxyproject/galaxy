"""
This script adds a foreign key to the form_values table in the galaxy_user table
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

    col = Column("form_values_id", Integer, ForeignKey('form_values.id', name='user_form_values_id_fk'), index=True)
    add_column(col, 'galaxy_user', metadata, index_name='ix_galaxy_user_form_values_id')


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('form_values_id', 'galaxy_user', metadata)
