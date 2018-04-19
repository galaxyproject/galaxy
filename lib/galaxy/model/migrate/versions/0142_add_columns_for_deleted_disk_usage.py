"""
Migration script to add 'deleted_disk_usage' column to the User table.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, MetaData, Numeric, Table

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    try:
        User_table = Table("galaxy_user", metadata, autoload=True)
        c = Column('deleted_disk_usage', Numeric(15, 0), index=True)
        c.create(User_table, index_name="ix_galaxy_user_deleted_disk_usage")
        assert c is User_table.c.deleted_disk_usage
    except Exception:
        log.exception("Adding deleted_disk_usage column to galaxy_user table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        User_table = Table("galaxy_user", metadata, autoload=True)
        User_table.c.deleted_disk_usage.drop()
    except Exception:
        log.exception("Dropping deleted_disk_usage column from galaxy_user table failed.")
