"""
Migration script to update the deferred job parameters for liftover transfer jobs.
"""

from sqlalchemy import *
from migrate import *
from sqlalchemy.orm import *

import datetime
now = datetime.datetime.utcnow

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *
from galaxy.model.orm.ext.assignmapper import assign_mapper

import sys, logging
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

context = scoped_session( sessionmaker( autoflush=False, autocommit=True ) )

metadata = MetaData( migrate_engine )

class DeferredJob( object ):
    states = Bunch( NEW = 'new',
                    WAITING = 'waiting',
                    QUEUED = 'queued',
                    RUNNING = 'running',
                    OK = 'ok',
                    ERROR = 'error' )
    def __init__( self, state=None, plugin=None, params=None ):
        self.state = state
        self.plugin = plugin
        self.params = params

DeferredJob.table = Table( "deferred_job", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "state", String( 64 ), index=True ),
    Column( "plugin", String( 128 ), index=True ),
    Column( "params", JSONType ) )

assign_mapper( context, DeferredJob, DeferredJob.table, properties = {} )

def upgrade():
    print __doc__
    liftoverjobs = dict()
    
    jobs = context.query( DeferredJob ).filter_by( plugin='LiftOverTransferPlugin' ).all()
    
    for job in jobs:
        if job.params[ 'parentjob' ] not in liftoverjobs:
            liftoverjobs[ job.params[ 'parentjob' ] ] = []
        liftoverjobs[ job.params[ 'parentjob'] ].append( job.id )
    
    for parent in liftoverjobs:
        lifts = liftoverjobs[ parent ]
        deferred = context.query( DeferredJob ).filter_by( id=parent ).first()
        deferred.params[ 'liftover' ] = lifts
        
    context.flush()

def downgrade():
    
    jobs = context.query( DeferredJob ).filter_by( plugin='GenomeTransferPlugin' ).all()
    
    for job in jobs:
        if len( job.params[ 'liftover' ] ) == 0:
            continue
        transfers = []
        for lift in job.params[ 'liftover' ]:
            liftoverjob = context.query( DeferredJob ).filter_by( id=lift ).first()
            transfers.append( liftoverjob.params[ 'transfer_job_id' ] )
        job.params[ 'liftover' ] = transfers
    
    context.flush()
