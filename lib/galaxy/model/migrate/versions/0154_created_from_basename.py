"""
Adds created_from_basename to dataset.
"""
import datetime
import logging

from sqlalchemy import (
    Column,
    MetaData,
    TEXT
)

from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column
)

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    created_from_basename_column = Column("created_from_basename", TEXT, default=None)
    add_column(created_from_basename_column, 'dataset', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('created_from_basename', 'dataset', metadata)
