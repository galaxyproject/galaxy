"""
Migration script to add session update time (used for timeouts)
"""

import logging

from sqlalchemy import Column, DateTime, MetaData

from galaxy.model.migrate.versions.util import add_column, drop_column

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    lastaction_column = Column("last_action", DateTime)
    add_column(lastaction_column, "galaxy_session", metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column("last_action", "galaxy_session", metadata)
