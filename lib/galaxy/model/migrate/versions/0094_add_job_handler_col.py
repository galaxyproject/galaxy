"""
Migration script to create "handler" column in job table.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import logging
log = logging.getLogger( __name__ )

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

metadata = MetaData()

# Column to add.
handler_col = Column( "handler", TrimmedString(255), index=True )

def display_migration_details():
    print ""
    print "This migration script adds a 'handler' column to the Job table."

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()

    # Add column to Job table.
    try:
        Job_table = Table( "job", metadata, autoload=True )
        handler_col.create( Job_table, index_name="ix_job_handler" )
        assert handler_col is Job_table.c.handler

    except Exception, e:
        print str(e)
        log.debug( "Adding column 'handler' to job table failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop column from Job table.
    try:
        Job_table = Table( "job", metadata, autoload=True )
        handler_col = Job_table.c.handler
        handler_col.drop()
    except Exception, e:
        log.debug( "Dropping column 'handler' from job table failed: %s" % ( str( e ) ) )
