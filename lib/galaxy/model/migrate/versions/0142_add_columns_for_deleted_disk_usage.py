"""
Migration script to add 'deleted_disk_usage' column to the User table.
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, DECIMAL, MetaData, Table

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    try:
        User_table = Table("galaxy_user", metadata, autoload=True)
        c = Column('deleted_disk_usage', DECIMAL(asdecimal=False), index=True)
        c.create(User_table, index_name="ix_galaxy_user_deleted_disk_usage")
        assert c is User_table.c.deleted_disk_usage
    except Exception:
        log.exception("Adding deleted_disk_usage column to galaxy_user table failed.")

    try:
        User_table = Table("galaxy_user", metadata, autoload=True)
        User_table.c.disk_usage.alter(type=DECIMAL(asdecimal=False))
    except Exception:
        log.exception("Altering data type of disk_usage column in galaxy_user table failed.")

    try:
        Galaxy_session_table = Table("galaxy_session", metadata, autoload=True)
        Galaxy_session_table.c.disk_usage.alter(type=DECIMAL(asdecimal=False))
    except Exception:
        log.exception("Altering data type of disk_usage column in galaxy_session table failed.")

    try:
        Dataset_table = Table("dataset", metadata, autoload=True)
        Dataset_table.c.total_size.alter(type=DECIMAL(asdecimal=False))
    except Exception:
        log.exception("Altering data type of total_size column in dataset table failed.")

    try:
        Dataset_table = Table("dataset", metadata, autoload=True)
        Dataset_table.c.file_size.alter(type=DECIMAL(asdecimal=False))
    except Exception:
        log.exception("Altering data type of file_size column in dataset table failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        User_table = Table("galaxy_user", metadata, autoload=True)
        User_table.c.deleted_disk_usage.drop()
    except Exception:
        log.exception("Dropping deleted_disk_usage column from galaxy_user table failed.")
