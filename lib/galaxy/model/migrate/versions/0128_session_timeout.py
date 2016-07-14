"""
Migration script to add session update time (used for timeouts)
"""
from __future__ import print_function

import datetime
import logging

from sqlalchemy import Column, DateTime, MetaData, Table

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    lastaction_column = Column( "last_action", DateTime )
    __add_column( lastaction_column, "galaxy_session", metadata )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    __drop_column( "last_action", "galaxy_session", metadata )


def __add_column(column, table_name, metadata, **kwds):
    try:
        table = Table( table_name, metadata, autoload=True )
        column.create( table, **kwds )
    except Exception as e:
        print(str(e))
        log.exception( "Adding column %s failed." % column)


def __drop_column( column_name, table_name, metadata ):
    try:
        table = Table( table_name, metadata, autoload=True )
        getattr( table.c, column_name ).drop()
    except Exception as e:
        print(str(e))
        log.exception( "Dropping column %s failed." % column_name )
