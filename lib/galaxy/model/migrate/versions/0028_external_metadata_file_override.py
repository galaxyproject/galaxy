"""
This script adds the filename_override_metadata column to the JobExternalOutputMetadata table,
allowing existing metadata files to be written when using external metadata and a cluster
set up with read-only access to database/files
"""
from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
import datetime
now = datetime.datetime.utcnow
import sys, logging
# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()

def display_migration_details():
    print "========================================"
    print "This script adds the filename_override_metadata column to the JobExternalOutputMetadata table,"
    print" allowing existing metadata files to be written when using external metadata and a cluster"
    print "set up with read-only access to database/files"
    print "========================================"

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    display_migration_details()
    # Load existing tables
    metadata.reflect()
    try:
        job_external_output_metadata = Table( "job_external_output_metadata", metadata, autoload=True )
        col = Column( "filename_override_metadata", String( 255 ) )
        col.create( job_external_output_metadata )
        assert col is job_external_output_metadata.c.filename_override_metadata
    except Exception, e:
        log.debug( "Adding column 'filename_override_metadata' to job_external_output_metadata table failed: %s" % ( str( e ) ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    pass
