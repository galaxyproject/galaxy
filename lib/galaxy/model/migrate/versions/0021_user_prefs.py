"""
This migration script adds a user preferences table to Galaxy.
"""

import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, Unicode

from galaxy.model.migrate.versions.util import create_table, drop_table

log = logging.getLogger(__name__)
metadata = MetaData()

# New table to support user preferences.
UserPreference_table = Table("user_preference", metadata,
                             Column("id", Integer, primary_key=True),
                             Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                             Column("name", Unicode(255), index=True),
                             Column("value", Unicode(1024)))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(UserPreference_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(UserPreference_table)
