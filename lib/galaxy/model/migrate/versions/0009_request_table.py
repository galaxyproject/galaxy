"""
This migration script adds a new column to 2 tables:
1) a new boolean type column named 'submitted' to the 'request' table
2) a new string type column named 'bar_code' to the 'sample' table
"""
from __future__ import print_function

import logging
import sys

from sqlalchemy import Boolean, Column, MetaData, Table

from galaxy.model.custom_types import TrimmedString

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()


def display_migration_details():
    print("========================================")
    print("This migration script adds a new column to 2 tables:")
    print("1) a new boolean type column named 'submitted' to the 'request' table")
    print("2) a new string type column named 'bar_code' to the 'sample' table")
    print("========================================")


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    display_migration_details()
    # Load existing tables
    Request_table = Table( "request", metadata, autoload=True )
    Sample_table = Table( "sample", metadata, autoload=True )
    metadata.reflect()
    # Add 1 column to the request table
    if Request_table is not None:
        try:
            col = Column( 'submitted', Boolean, default=False )
            col.create( Request_table)
            assert col is Request_table.c.submitted
        except Exception as e:
            log.debug( "Adding column 'submitted' to request table failed: %s" % ( str( e ) ) )

    # Add 1 column to the sample table
    if Sample_table is not None:
        try:
            col = Column( "bar_code", TrimmedString( 255 ), index=True )
            col.create( Sample_table, index_name='ix_sample_bar_code')
            assert col is Sample_table.c.bar_code
        except Exception as e:
            log.debug( "Adding column 'bar_code' to sample table failed: %s" % ( str( e ) ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    pass
