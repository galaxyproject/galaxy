"""
Migration script to create "params" column in job table.
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
params_col = Column( "params", TrimmedString(255), index=True )

def display_migration_details():
    print ""
    print "This migration script adds a 'params' column to the Job table."

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()

    # Add column to Job table.
    try:
        Job_table = Table( "job", metadata, autoload=True )
        params_col.create( Job_table, index_name="ix_job_params")
        assert params_col is Job_table.c.params

    except Exception, e:
        print str(e)
        log.debug( "Adding column 'params' to job table failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop column from Job table.
    try:
        Job_table = Table( "job", metadata, autoload=True )
        params_col = Job_table.c.params
        params_col.drop()
    except Exception, e:
        log.debug( "Dropping column 'params' from job table failed: %s" % ( str( e ) ) )
