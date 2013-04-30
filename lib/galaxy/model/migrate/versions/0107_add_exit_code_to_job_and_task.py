"""
Add the exit_code column to the Job and Task tables.
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

# There was a bug when only one column was used for both tables,
# so create separate columns.
exit_code_job_col = Column( "exit_code", Integer, nullable=True )
exit_code_task_col = Column( "exit_code", Integer, nullable=True )

def display_migration_details():
    print ""
    print "This migration script adds a 'handler' column to the Job table."

def upgrade(migrate_engine):
    print __doc__
    metadata.bind = migrate_engine
    metadata.reflect()

    # Add the exit_code column to the Job table.
    try:
        job_table = Table( "job", metadata, autoload=True )
        exit_code_job_col.create( job_table )
        assert exit_code_job_col is job_table.c.exit_code
    except Exception, e:
        print str(e)
        log.error( "Adding column 'exit_code' to job table failed: %s" % str( e ) )
        return

    # Add the exit_code column to the Task table.
    try:
        task_table = Table( "task", metadata, autoload=True )
        exit_code_task_col.create( task_table )
        assert exit_code_task_col is task_table.c.exit_code
    except Exception, e:
        print str(e)
        log.error( "Adding column 'exit_code' to task table failed: %s" % str( e ) )
        return

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop the Job table's exit_code column.
    try:
        job_table = Table( "job", metadata, autoload=True )
        exit_code_col = job_table.c.exit_code
        exit_code_col.drop()
    except Exception, e:
        log.debug( "Dropping 'exit_code' column from job table failed: %s" % ( str( e ) ) )

    # Drop the Job table's exit_code column.
    try:
        task_table = Table( "task", metadata, autoload=True )
        exit_code_col = task_table.c.exit_code
        exit_code_col.drop()
    except Exception, e:
        log.debug( "Dropping 'exit_code' column from task table failed: %s" % ( str( e ) ) )

