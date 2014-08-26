"""
Add UUIDs to workflows
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
from galaxy.model.custom_types import UUIDType, TrimmedString

import logging
log = logging.getLogger( __name__ )

metadata = MetaData()



"""
Because both workflow and job requests can be determined 
based the a fixed data structure, their IDs are based on
hashing the data structure 
"""
workflow_uuid_column = Column( "uuid", UUIDType, nullable=True )


def display_migration_details():
    print "This migration script adds a UUID column to workflows"

def upgrade(migrate_engine):
    print __doc__
    metadata.bind = migrate_engine
    metadata.reflect()

    # Add the uuid colum to the workflow table
    try:
        workflow_table = Table( "workflow", metadata, autoload=True )
        workflow_uuid_column.create( workflow_table )
        assert workflow_uuid_column is workflow_table.c.uuid
    except Exception, e:
        print str(e)
        log.error( "Adding column 'uuid' to workflow table failed: %s" % str( e ) )
        return

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop the workflow table's uuid column.
    try:
        workflow_table = Table( "workflow", metadata, autoload=True )
        workflow_uuid = workflow_table.c.uuid
        workflow_uuid.drop()
    except Exception, e:
        log.debug( "Dropping 'uuid' column from workflow table failed: %s" % ( str( e ) ) )

