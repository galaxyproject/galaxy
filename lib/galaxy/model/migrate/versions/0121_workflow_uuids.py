"""
Add UUIDs to workflows
"""
from __future__ import print_function

import logging

from sqlalchemy import Column, MetaData, Table

from galaxy.model.custom_types import UUIDType

log = logging.getLogger( __name__ )
metadata = MetaData()


"""
Because both workflow and job requests can be determined
based the a fixed data structure, their IDs are based on
hashing the data structure
"""
workflow_uuid_column = Column( "uuid", UUIDType, nullable=True )


def display_migration_details():
    print("This migration script adds a UUID column to workflows")


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # Add the uuid colum to the workflow table
    try:
        workflow_table = Table( "workflow", metadata, autoload=True )
        workflow_uuid_column.create( workflow_table )
        assert workflow_uuid_column is workflow_table.c.uuid
    except Exception as e:
        print(str(e))
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
    except Exception as e:
        log.debug( "Dropping 'uuid' column from workflow table failed: %s" % ( str( e ) ) )
