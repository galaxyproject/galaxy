"""
This script adds the filename_override_metadata column to the JobExternalOutputMetadata table,
allowing existing metadata files to be written when using external metadata and a cluster
set up with read-only access to database/files
"""
from __future__ import print_function

import datetime
import logging
import sys

from sqlalchemy import Column, MetaData, String, Table

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    # Load existing tables
    metadata.reflect()
    try:
        job_external_output_metadata = Table( "job_external_output_metadata", metadata, autoload=True )
        col = Column( "filename_override_metadata", String( 255 ) )
        col.create( job_external_output_metadata )
        assert col is job_external_output_metadata.c.filename_override_metadata
    except Exception as e:
        log.debug( "Adding column 'filename_override_metadata' to job_external_output_metadata table failed: %s" % ( str( e ) ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    pass
