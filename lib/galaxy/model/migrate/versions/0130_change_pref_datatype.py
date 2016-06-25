"""
Migration script to change the value column of user_preference from varchar to text.
"""

from sqlalchemy import MetaData, Table, Text

import datetime
now = datetime.datetime.utcnow

import logging
log = logging.getLogger( __name__ )

metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()
    t = Table("user_preference", metadata, autoload=True)
    t.c.value.alter(type=Text)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    # Pass, since we don't want to potentially truncate data.
