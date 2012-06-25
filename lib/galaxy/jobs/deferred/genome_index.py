"""
Module for managing genome transfer jobs.
"""
from __future__ import with_statement

import logging, shutil, gzip, bz2, zipfile, tempfile, tarfile, sys, os

from galaxy import eggs
from sqlalchemy import and_
from data_transfer import *

log = logging.getLogger( __name__ )

__all__ = [ 'GenomeIndexPlugin' ]

class GenomeIndexPlugin( DataTransfer ):
    
    def __init__( self, app ):
        super( GenomeIndexPlugin, self ).__init__( app )
        self.app = app
        self.tool = app.toolbox.tools_by_id['__GENOME_INDEX__']
        self.sa_session = app.model.context.current

    def create_job( self, trans, path, indexes, dbkey, intname ):
        params = dict( user=trans.user.id, path=path, indexes=indexes, dbkey=dbkey, intname=intname )
        deferred = trans.app.model.DeferredJob( state = self.app.model.DeferredJob.states.NEW, plugin = 'GenomeIndexPlugin', params = params )
        self.sa_session.add( deferred )
        self.sa_session.flush()
        log.debug( 'Job created, id %d' % deferred.id )
        return deferred.id
        
    def check_job( self, job ):
        log.debug( 'Job check' )
        return 'ready'
    
    def run_job( self, job ):
        incoming = dict( path=os.path.abspath( job.params[ 'path' ] ), indexer=job.params[ 'indexes' ][0], user=job.params[ 'user' ] )
        indexjob = self.tool.execute( self, set_output_hid=False, history=None, incoming=incoming, transfer=None, deferred=job )
        job.params[ 'indexjob' ] = indexjob[0].id
        job.state = self.app.model.DeferredJob.states.RUNNING
        self.sa_session.add( job )
        self.sa_session.flush()
        return self.app.model.DeferredJob.states.RUNNING
