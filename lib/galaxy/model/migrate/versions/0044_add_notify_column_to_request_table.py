"""
Migration script to add a notify column to the request table.
"""
from __future__ import print_function

import logging

from sqlalchemy import (
    Boolean,
    Column,
    MetaData
)

from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column,
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    c = Column("notify", Boolean, default=False)
    add_column(c, 'request', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('notify', 'request', metadata)
