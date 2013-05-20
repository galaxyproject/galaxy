"""
Add support for job destinations to the job table
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
from galaxy.model.custom_types import JSONType

import logging
log = logging.getLogger( __name__ )

def display_migration_details():
    print ""
    print "This migration script adds 'destination_id' and 'destination_params' columns to the Job table."

def upgrade(migrate_engine):
    print __doc__
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()
    Job_table = Table( "job", metadata, autoload=True )

    c = Column( "destination_id", String( 255 ), nullable=True )
    try:
        c.create( Job_table )
        assert c is Job_table.c.destination_id
    except Exception, e:
        log.error( "Adding column 'destination_id' to job table failed: %s" % str( e ) )

    c = Column( "destination_params", JSONType, nullable=True )
    try:
        c.create( Job_table )
        assert c is Job_table.c.destination_params
    except Exception, e:
        log.error( "Adding column 'destination_params' to job table failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()
    Job_table = Table( "job", metadata, autoload=True )

    try:
        Job_table.c.destination_params.drop()
    except Exception, e:
        log.error( "Dropping column 'destination_params' from job table failed: %s" % str( e ) )

    try:
        Job_table.c.destination_id.drop()
    except Exception, e:
        log.error( "Dropping column 'destination_id' from job table failed: %s" % str( e ) )
