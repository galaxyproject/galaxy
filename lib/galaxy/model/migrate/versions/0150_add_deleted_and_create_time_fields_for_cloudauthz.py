"""
Adds `deleted` and `create_time` columns to cloudauthz table.
"""

from __future__ import print_function

import logging

from sqlalchemy import Boolean, Column, DateTime, MetaData, Table

from galaxy.model.migrate.versions.util import add_column, drop_column

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    cloudauthz_table = Table("cloudauthz", metadata, autoload=True)
    create_time_column = Column('create_time', DateTime)
    add_column(create_time_column, cloudauthz_table)

    deleted_column = Column('deleted', Boolean)
    add_column(deleted_column, cloudauthz_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    cloudauthz_table = Table("cloudauthz", metadata, autoload=True)
    # SQLAlchemy Migrate has a bug when dropping a boolean column in SQLite
    if migrate_engine.name != 'sqlite':
        drop_column('deleted', cloudauthz_table)
    drop_column('create_time', cloudauthz_table)
