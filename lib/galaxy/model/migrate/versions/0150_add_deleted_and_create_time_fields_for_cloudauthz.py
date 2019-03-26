"""
Adds `deleted` and `create_time` columns to cloudauthz table.
"""

from __future__ import print_function

import logging

from sqlalchemy import Boolean, Column, DateTime, MetaData, Table

log = logging.getLogger(__name__)
create_time_column = Column('create_time', DateTime)
deleted_column = Column('deleted', Boolean)


def upgrade(migrate_engine):
    print(__doc__)
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    cloudauthz_table = Table("cloudauthz", metadata, autoload=True)

    try:
        create_time_column.create(cloudauthz_table)
        assert create_time_column is cloudauthz_table.c.create_time
    except Exception:
        log.exception("Adding column 'create_time' to `cloudauthz` table failed.")

    try:
        deleted_column.create(cloudauthz_table)
        assert deleted_column is cloudauthz_table.c.deleted
    except Exception:
        log.exception("Adding column 'deleted' to `cloudauthz` table failed.")


def downgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    cloudauthz_table = Table("cloudauthz", metadata, autoload=True)

    try:
        column = cloudauthz_table.c.create_time
        column.drop()
    except Exception:
        log.exception("Dropping 'create_time' column from `cloudauthz` table failed.")

    try:
        column = cloudauthz_table.c.deleted
        column.drop()
    except Exception:
        log.exception("Dropping 'deleted' column from `cloudauthz` table failed.")
