"""
Migration script to add a notify column to the request table.
"""
from __future__ import print_function

import logging

from sqlalchemy import Boolean, Column, MetaData, Table

log = logging.getLogger( __name__ )
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    Request_table = Table( "request", metadata, autoload=True )
    c = Column( "notify", Boolean, default=False  )
    c.create( Request_table )
    assert c is Request_table.c.notify


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    pass
