"""
Migration script to create table for storing deferred job and managed transfer
information.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

from galaxy.model.custom_types import *

import datetime
now = datetime.datetime.utcnow

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

# Table to add

DeferredJob_table = Table( "deferred_job", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "state", String( 64 ), index=True ),
    Column( "plugin", String( 128 ), index=True ),
    Column( "params", JSONType ) )

TransferJob_table = Table( "transfer_job", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "state", String( 64 ), index=True ),
    Column( "path", String( 1024 ) ),
    Column( "params", JSONType ) )

def upgrade():
    print __doc__
    metadata.reflect()
    
    # Create deferred_job table
    try:
        DeferredJob_table.create()
    except Exception, e:
        log.error( "Creating deferred_job table failed: %s" % str( e ) )
        
    # Create transfer_job table
    try:
        TransferJob_table.create()
    except Exception, e:
        log.error( "Creating transfer_job table failed: %s" % str( e ) )
        
def downgrade():
    metadata.reflect()
    
    # Drop deferred_job table
    try:
        DeferredJob_table.drop()
    except Exception, e:
        log.error( "Dropping deferred_job table failed: %s" % str( e ) )

    # Drop transfer_job table
    try:
        TransferJob_table.drop()
    except Exception, e:
        log.error( "Dropping transfer_job table failed: %s" % str( e ) )
