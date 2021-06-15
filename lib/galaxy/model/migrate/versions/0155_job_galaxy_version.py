"""
Add 'galaxy_version' attribute to Job table.
"""

import datetime
import logging

from sqlalchemy import (
    Column,
    MetaData,
    String
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

    created_from_basename_column = Column("galaxy_version", String(64), default=None)
    add_column(created_from_basename_column, 'job', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('galaxy_version', 'job', metadata)
