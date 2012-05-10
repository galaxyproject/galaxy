"""
Module for managing genome transfer jobs.
"""
import logging, shutil, gzip, tempfile, sys

from galaxy import eggs
from sqlalchemy import and_

from galaxy.util.odict import odict
from galaxy.workflow.modules import module_factory
from galaxy.jobs.actions.post import ActionBox

from galaxy.tools.parameters import visit_input_values
from galaxy.tools.parameters.basic import DataToolParameter
from galaxy.tools.data import ToolDataTableManager

from galaxy.datatypes.checkers import *

from data_transfer import *

log = logging.getLogger( __name__ )

__all__ = [ 'LiftOverTransferPlugin' ]

class LiftOverTransferPlugin( DataTransfer ):
    
    locations = {}
    
    def __init__( self, app ):
        super( LiftOverTransferPlugin, self ).__init__( app )
        self.app = app
        self.sa_session = app.model.context.current
        
    def create_job( self, trans, url, dbkey, from_genome, to_genome, destfile ):
        job = trans.app.transfer_manager.new( protocol='http', url=url )
        params = dict( user=trans.user.id, transfer_job_id=job.id, protocol='http', 
                       type='init_transfer', dbkey=dbkey, from_genome=from_genome, 
                       to_genome=to_genome, destfile=destfile )
        deferred = trans.app.model.DeferredJob( state = self.app.model.DeferredJob.states.NEW, plugin = 'LiftOverTransferPlugin', params = params )
        self.sa_session.add( deferred )
        self.sa_session.flush()
        return deferred.id
        
    def check_job( self, job ):
        if job.params['type'] == 'init_transfer': 
            if not hasattr(job, 'transfer_job'):
                job.transfer_job = self.sa_session.query( self.app.model.TransferJob ).get( int( job.params[ 'transfer_job_id' ] ) )
            else:
                self.sa_session.refresh( job.transfer_job )
            if job.transfer_job.state == 'done':
                transfer = job.transfer_job
                transfer.state = 'downloaded'
                job.params['type'] = 'extract_transfer'
                self.sa_session.add( job )
                self.sa_session.add( transfer )
                self.sa_session.flush()
                return self.job_states.READY
            elif job.transfer_job.state == 'running':
                return self.job_states.WAIT
            elif job.transfer_job.state == 'new':
                assert job.params[ 'protocol' ] in [ 'http', 'ftp', 'https' ], 'Unknown protocol %s' % job.params[ 'protocol' ]
                self.app.transfer_manager.run( job.transfer_job )
                self.sa_session.add( job.transfer_job )
                self.sa_session.flush()
                return self.job_states.WAIT
            else:
                log.error( "An error occurred while downloading from %s" % job.params[ 'url' ] )
                return self.job_states.INVALID
        elif job.params[ 'type' ] == 'extract_transfer': 
            return self.job_states.READY
            
    def get_job_status( self, jobid ):
        job = self.sa_session.query( self.app.model.DeferredJob ).get( int( jobid ) )
        return job
            
    def run_job( self, job ):
        params = job.params
        dbkey = params[ 'dbkey' ]
        source = params[ 'from_genome' ]
        target = params[ 'to_genome' ]
        if not hasattr( job, 'transfer_job' ):
            job.transfer_job = self.sa_session.query( self.app.model.TransferJob ).get( int( job.params[ 'transfer_job_id' ] ) )
        else:
            self.sa_session.refresh( job.transfer_job )
        transfer = job.transfer_job
        if params[ 'type' ] == 'extract_transfer':
            CHUNK_SIZE = 2**20
            destpath = os.path.join( self.app.config.get( 'genome_data_path', 'tool-data/genome' ), job.params[ 'dbkey' ], 'liftOver' )
            destfile = job.params[ 'destfile' ]
            destfilepath = os.path.join( destpath, destfile )
            tmpprefix = '%s_%s_download_unzip_' % ( job.params['dbkey'], job.params[ 'transfer_job_id' ] )
            tmppath = os.path.dirname( os.path.abspath( transfer.path ) )
            if not os.path.exists( destpath ):
                os.makedirs( destpath )
            fd, uncompressed = tempfile.mkstemp( prefix=tmpprefix, dir=tmppath, text=False )
            chain = gzip.open( transfer.path, 'rb' )
            while 1:
                try:
                    chunk = chain.read( CHUNK_SIZE )
                except IOError:
                    os.close( fd )
                    log.error( 'Problem decompressing compressed data' )
                    exit()
                if not chunk:
                    break
                os.write( fd, chunk )
            os.close( fd )
            chain.close()
            # Replace the gzipped file with the decompressed file if it's safe to do so
            shutil.move( uncompressed, destfilepath )
            os.remove( transfer.path )
            os.chmod( destfilepath, 0644 )
            locline = '\t'.join( [ source, target, os.path.abspath( destfilepath ) ] )
            self._add_line( locline )
            job.state = self.app.model.DeferredJob.states.OK
            job.params[ 'type' ] = 'finish_transfer'
            transfer.path = os.path.abspath(destfilepath)
            transfer.state = 'done'
            self.sa_session.add( job )
            self.sa_session.add( transfer )
            self.sa_session.flush()
            return self.app.model.DeferredJob.states.OK
                    
    def _add_line( self, newline ):
        filepath = 'tool-data/liftOver.loc'
        origlines = []
        with open( filepath, 'r' ) as destfile:
            for line in destfile:
                origlines.append( line.strip() )
        if newline not in origlines:
            origlines.append( newline )
            with open( filepath, 'w+' ) as destfile:
                destfile.write( '\n'.join( origlines ) )
        
