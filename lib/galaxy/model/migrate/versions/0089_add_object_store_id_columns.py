"""
Migration script to add 'object_store_id' column to various tables
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, MetaData, Table

from galaxy.model.custom_types import TrimmedString

log = logging.getLogger( __name__ )
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    for t_name in ( 'dataset', 'job', 'metadata_file' ):
        t = Table( t_name, metadata, autoload=True )
        c = Column( "object_store_id", TrimmedString( 255 ), index=True )
        try:
            c.create( t, index_name="ix_%s_object_store_id" % t_name)
            assert c is t.c.object_store_id
        except Exception as e:
            print("Adding object_store_id column to %s table failed: %s" % ( t_name, str( e ) ))
            log.debug( "Adding object_store_id column to %s table failed: %s" % ( t_name, str( e ) ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    for t_name in ( 'dataset', 'job', 'metadata_file' ):
        t = Table( t_name, metadata, autoload=True )
        try:
            t.c.object_store_id.drop()
        except Exception as e:
            print("Dropping object_store_id column from %s table failed: %s" % ( t_name, str( e ) ))
            log.debug( "Dropping object_store_id column from %s table failed: %s" % ( t_name, str( e ) ) )
