"""
Migration script to create table for exporting histories to archives.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData()

# Table to add.

JobExportHistoryArchive_table = Table( "job_export_history_archive", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "compressed", Boolean, index=True, default=False ),
    Column( "history_attrs_filename", TEXT ),
    Column( "datasets_attrs_filename", TEXT ),
    Column( "jobs_attrs_filename", TEXT )
    )

def upgrade(migrate_engine):
    print __doc__
    metadata.bind = migrate_engine
    metadata.reflect()

    # Create job_export_history_archive table.
    try:
        JobExportHistoryArchive_table.create()
    except Exception, e:
        print str(e)
        log.debug( "Creating job_export_history_archive table failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop job_export_history_archive table.
    try:
        JobExportHistoryArchive_table.drop()
    except Exception, e:
        print str(e)
        log.debug( "Dropping job_export_history_archive table failed: %s" % str( e ) )
