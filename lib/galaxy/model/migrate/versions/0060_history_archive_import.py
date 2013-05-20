"""
Migration script to create column and table for importing histories from
file archives.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData()

# Columns to add.

importing_col = Column( "importing", Boolean, index=True, default=False )
ldda_parent_col = Column( "ldda_parent_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), index=True )

# Table to add.

JobImportHistoryArchive_table = Table( "job_import_history_archive", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "archive_dir", TEXT )
    )

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print __doc__
    metadata.reflect()

    # Add column to history table and initialize.
    try:
        History_table = Table( "history", metadata, autoload=True )
        importing_col.create( History_table, index_name="ix_history_importing")
        assert importing_col is History_table.c.importing

        # Initialize column to false.
        if migrate_engine.name == 'mysql' or migrate_engine.name == 'sqlite':
            default_false = "0"
        elif migrate_engine.name in ['postgres', 'postgresql']:
            default_false = "false"
        migrate_engine.execute( "UPDATE history SET importing=%s" % default_false )
    except Exception, e:
        print str(e)
        log.debug( "Adding column 'importing' to history table failed: %s" % str( e ) )

    # Create job_import_history_archive table.
    try:
        JobImportHistoryArchive_table.create()
    except Exception, e:
        log.debug( "Creating job_import_history_archive table failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop 'importing' column from history table.
    try:
        History_table = Table( "history", metadata, autoload=True )
        importing_col = History_table.c.importing
        importing_col.drop()
    except Exception, e:
        log.debug( "Dropping column 'importing' from history table failed: %s" % ( str( e ) ) )

    # Drop job_import_history_archive table.
    try:
        JobImportHistoryArchive_table.drop()
    except Exception, e:
        log.debug( "Dropping job_import_history_archive table failed: %s" % str( e ) )
