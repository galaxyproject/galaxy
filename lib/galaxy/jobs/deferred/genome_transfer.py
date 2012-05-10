"""
Module for managing genome transfer jobs.
"""
import logging, shutil, gzip, bz2, zipfile, tempfile, tarfile, sys

from galaxy import eggs
from sqlalchemy import and_

from galaxy.util.odict import odict
from galaxy.workflow.modules import module_factory
from galaxy.jobs.actions.post import ActionBox

from galaxy.tools.parameters import visit_input_values
from galaxy.tools.parameters.basic import DataToolParameter
from galaxy.tools.data import ToolDataTableManager

from galaxy.datatypes.checkers import *
from galaxy.datatypes.sequence import Fasta
from data_transfer import *

log = logging.getLogger( __name__ )

__all__ = [ 'GenomeTransferPlugin' ]

class GenomeTransferPlugin( DataTransfer ):
    
    locations = {}
    
    def __init__( self, app ):
        super( GenomeTransferPlugin, self ).__init__( app )
        self.app = app
        self.tool = app.toolbox.tools_by_id['__GENOME_INDEX__']
        self.sa_session = app.model.context.current
        tdtman = ToolDataTableManager()
        xmltree = tdtman.load_from_config_file(app.config.tool_data_table_config_path)
        for node in xmltree:
            table = node.get('name')
            location = node.findall('file')[0].get('path')
            self.locations[table] = location
        
    def create_job( self, trans, url, dbkey, intname, indexes ):
        job = trans.app.transfer_manager.new( protocol='http', url=url )
        params = dict( user=trans.user.id, transfer_job_id=job.id, protocol='http', type='init_transfer', url=url, dbkey=dbkey, indexes=indexes, intname=intname, liftover=None )
        deferred = trans.app.model.DeferredJob( state = self.app.model.DeferredJob.states.NEW, plugin = 'GenomeTransferPlugin', params = params )
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
        if not hasattr( job, 'transfer_job' ):
            job.transfer_job = self.sa_session.query( self.app.model.TransferJob ).get( int( job.params[ 'transfer_job_id' ] ) )
        else:
            self.sa_session.refresh( job.transfer_job )
        return job
            
    def run_job( self, job ):
        params = job.params
        dbkey = params[ 'dbkey' ]
        if not hasattr( job, 'transfer_job' ):
            job.transfer_job = self.sa_session.query( self.app.model.TransferJob ).get( int( job.params[ 'transfer_job_id' ] ) )
        else:
            self.sa_session.refresh( job.transfer_job )
        transfer = job.transfer_job
        if params[ 'type' ] == 'extract_transfer':
            CHUNK_SIZE = 2**20
            destpath = os.path.join( self.app.config.get( 'genome_data_path', 'tool-data/genome' ), job.params[ 'dbkey' ], 'seq' )
            destfile = '%s.fa' % job.params[ 'dbkey' ]
            destfilepath = os.path.join( destpath, destfile )
            tmpprefix = '%s_%s_download_unzip_' % ( job.params['dbkey'], job.params[ 'transfer_job_id' ] )
            tmppath = os.path.dirname( os.path.abspath( transfer.path ) )
            if not os.path.exists( destpath ):
                os.makedirs( destpath )
            protocol = job.params[ 'protocol' ]
            data_type = self._check_compress( transfer.path )
            if data_type is None:
                sniffer = Fasta()
                if sniffer.sniff( transfer.path ):
                    data_type = 'fasta'
            fd, uncompressed = tempfile.mkstemp( prefix=tmpprefix, dir=tmppath, text=False )
            if data_type in [ 'tar.gzip', 'tar.bzip' ]:
                fp = open( transfer.path, 'r' )
                tar = tarfile.open( mode = 'r:*', bufsize = CHUNK_SIZE, fileobj = fp )
                files = tar.getmembers()
                for filename in files:
                    z = tar.extractfile(filename)
                    try:
                        chunk = z.read( CHUNK_SIZE )
                    except IOError:
                        os.close( fd )
                        log.error( 'Problem decompressing compressed data' )
                        exit()
                    if not chunk:
                        break
                    os.write( fd, chunk )
                    os.write( fd, '\n' )
                os.close( fd )
                tar.close()
                fp.close()
            elif data_type == 'gzip':
                compressed = gzip.open( transfer.path, mode = 'rb' )
                while 1:
                    try:
                        chunk = compressed.read( CHUNK_SIZE )
                    except IOError:
                        compressed.close()
                        log.error( 'Problem decompressing compressed data' )
                        exit()
                    if not chunk:
                        break
                    os.write( fd, chunk )
                    os.write( fd, '\n' )
                os.close( fd )
                compressed.close()
            elif data_type == 'bzip':
                compressed = bz2.BZ2File( transfer.path, mode = 'r' )
                while 1:
                    try:
                        chunk = compressed.read( CHUNK_SIZE )
                    except IOError:
                        compressed.close()
                        log.error( 'Problem decompressing compressed data' )
                        exit()
                    if not chunk:
                        break
                    os.write( fd, chunk )
                    os.write( fd, '\n' )
                os.close( fd )
                compressed.close()
            elif data_type == 'zip':
                uncompressed_name = None
                unzipped = False
                z = zipfile.ZipFile( transfer.path )
                z.debug = 3
                for name in z.namelist():
                    if name.endswith('/'):
                        continue
                    if sys.version_info[:2] >= ( 2, 6 ):
                        zipped_file = z.open( name )
                        while 1:
                            try:
                                chunk = zipped_file.read( CHUNK_SIZE )
                            except IOError:
                                os.close( fd )
                                log.error( 'Problem decompressing zipped data' )
                                return self.app.model.DeferredJob.states.INVALID
                            if not chunk:
                                break
                            os.write( fd, chunk )
                            os.write( fd, '\n' )
                        zipped_file.close()
                    else:
                        try:
                            outfile = open( fd, 'wb' )
                            outfile.write( z.read( name ) )
                            outfile.close()
                        except IOError:
                            os.close( fd )
                            log.error( 'Problem decompressing zipped data' )
                            return
                os.close( fd )
                z.close()
            elif data_type == 'fasta':
                uncompressed = transfer.path
            else:
                job.state = self.app.model.DeferredJob.states.INVALID
                log.error( "Unrecognized compression format for file %s." % transfer.path )
                self.sa_session.add( job )
                self.sa_session.flush()
                return
            shutil.move( uncompressed, destfilepath )
            if os.path.exists( transfer.path ):
                os.remove( transfer.path )
            os.chmod( destfilepath, 0644 )
            fastaline = '\t'.join( [ dbkey, dbkey, params[ 'intname' ], os.path.abspath( destfilepath ) ] )
            self._add_line( 'all_fasta', fastaline )
            job.state = self.app.model.DeferredJob.states.OK
            job.params[ 'type' ] = 'finish_transfer'
            transfer.path = os.path.abspath(destfilepath)
            transfer.state = 'done'
            self.sa_session.add( job )
            self.sa_session.add( transfer )
            self.sa_session.flush()
            if transfer.state == 'done' and params[ 'indexes' ] is not None:
                for indexer in params[ 'indexes' ]:
                    incoming = dict(indexer=indexer, dbkey=params[ 'dbkey' ], intname=params[ 'intname' ], path=transfer.path, user=params['user']  )
                    deferred = self.tool.execute( self, set_output_hid=False, history=None, incoming=incoming, transfer=transfer, deferred=job )
            return self.app.model.DeferredJob.states.OK
                    
    def _check_compress( self, filepath ):
        retval = ''
        if tarfile.is_tarfile( filepath ):
            retval = 'tar.'
        if check_zip( filepath ):
            return 'zip'
        is_bzipped, is_valid = check_bz2( filepath )
        if is_bzipped and is_valid:
            return retval + 'bzip'
        is_gzipped, is_valid = check_gzip( filepath )
        if is_gzipped and is_valid:
            return retval + 'gzip'
        return None
        
    def _add_line( self, locfile, newline ):
        filepath = self.locations[ locfile ]
        origlines = []
        output = []
        comments = []
        with open( filepath, 'r' ) as destfile:
            for line in destfile:
                if line.startswith( '#' ):
                    comments.append( line.strip() )
                else:
                    origlines.append( line.strip() )
        if newline not in origlines:
            origlines.append( newline )
            output.extend( comments )
            origlines.sort()
            output.extend( origlines )
            with open( filepath, 'w+' ) as destfile:
                destfile.write( '\n'.join( output ) )
        
