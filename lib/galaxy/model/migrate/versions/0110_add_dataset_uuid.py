"""
Add UUID column to dataset table
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
from galaxy.model.custom_types import UUIDType

import logging
log = logging.getLogger( __name__ )

dataset_uuid_column = Column( "uuid", UUIDType, nullable=True )


def display_migration_details():
    print ""
    print "This migration adds uuid column to dataset table"

def upgrade(migrate_engine):
    print __doc__
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    # Add the uuid colum to the dataset table
    try:
        dataset_table = Table( "dataset", metadata, autoload=True )
        dataset_uuid_column.create( dataset_table )
        assert dataset_uuid_column is dataset_table.c.uuid
    except Exception, e:
        print str(e)
        log.error( "Adding column 'uuid' to dataset table failed: %s" % str( e ) )
        return


def downgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop the dataset table's uuid column.
    try:
        dataset_table = Table( "dataset", metadata, autoload=True )
        dataset_uuid = dataset_table.c.uuid
        dataset_uuid.drop()
    except Exception, e:
        log.debug( "Dropping 'uuid' column from dataset table failed: %s" % ( str( e ) ) )


