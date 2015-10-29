"""
Migration script to update the deferred job parameters for liftover transfer jobs.
"""
import datetime
import logging
import sys

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table
from sqlalchemy.orm import mapper, scoped_session, sessionmaker

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import JSONType
from galaxy.util.bunch import Bunch

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()
context = scoped_session( sessionmaker( autoflush=False, autocommit=True ) )


class DeferredJob( object ):
    states = Bunch( NEW='new',
                    WAITING='waiting',
                    QUEUED='queued',
                    RUNNING='running',
                    OK='ok',
                    ERROR='error' )

    def __init__( self, state=None, plugin=None, params=None ):
        self.state = state
        self.plugin = plugin
        self.params = params


def upgrade(migrate_engine):
    metadata.bind = migrate_engine

    DeferredJob.table = Table( "deferred_job", metadata,
                               Column( "id", Integer, primary_key=True ),
                               Column( "create_time", DateTime, default=now ),
                               Column( "update_time", DateTime, default=now, onupdate=now ),
                               Column( "state", String( 64 ), index=True ),
                               Column( "plugin", String( 128 ), index=True ),
                               Column( "params", JSONType ) )

    mapper( DeferredJob, DeferredJob.table, properties={} )

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


def downgrade(migrate_engine):
    metadata.bind = migrate_engine

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
