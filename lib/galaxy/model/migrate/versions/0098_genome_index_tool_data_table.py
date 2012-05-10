"""
Migration script to create the genome_index_tool_data table.
"""

from sqlalchemy import *
from migrate import *

import datetime
now = datetime.datetime.utcnow

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

import sys, logging
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData( migrate_engine )

# New table in changeset TODO:TODO
GenomeIndexToolData_table = Table( "genome_index_tool_data", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "deferred_job_id", Integer, ForeignKey( "deferred_job.id" ), index=True ),
    Column( "transfer_job_id", Integer, ForeignKey( "transfer_job.id" ), index=True ),
    Column( "fasta_path", String( 255 ) ),
    Column( "created_time", DateTime, default=now ),
    Column( "modified_time", DateTime, default=now, onupdate=now ),
    Column( "indexer", String( 64 ) ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    )
    
def upgrade():
    print __doc__
    
    metadata.reflect()
    try:
        GenomeIndexToolData_table.create()
    except Exception, e:
        log.debug( "Creating genome_index_tool_data table failed: %s" % str( e ) )

def downgrade():
    metadata.reflect()
    try:
        GenomeIndexToolData_table.drop()
    except Exception, e:
        log.debug( "Dropping genome_index_tool_data table failed: %s" % str( e ) )
