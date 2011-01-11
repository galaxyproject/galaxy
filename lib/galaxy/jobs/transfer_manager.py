"""
Client interface to the Galaxy Transfer Manager, which is a standalone,
lightweight on-demand daemon.
"""
import subprocess, socket, logging

from galaxy import eggs
from galaxy.util import listify, json

log = logging.getLogger( __name__ )

class TransferManager( object ):
    def __init__( self, app ):
        self.app = app
        self.sa_session = app.model.context.current
        self.tm_port = app.config.transfer_manager_port
        self.tm_command = 'python transfer_manager.py'
        self.tm_transfer_job_id_flag = '-i'
    def new( self, path=None, **kwd ):
        if 'url' not in kwd:
            raise Exception( 'Missing required parameter "url".' )
        # try: except JSON:
        transfer_job = self.app.model.TransferJob( state=self.app.model.TransferJob.states.NEW,
                                                   params=kwd )
        self.sa_session.add( transfer_job )
        self.sa_session.flush()
        return transfer_job
    def run( self, transfer_jobs ):
        """
        This method blocks, so if invoking the transfer manager ever starts
        taking too long, we should move it to a thread.  However, the
        transfer_manager will either daemonize or return after submitting to a
        running daemon, so it should be fairly quick to return.
        """
        spaced_flag = ' %s ' % self.tm_transfer_job_id_flag
        cmd = '%s %s %s' % ( self.tm_command, self.tm_transfer_job_id_flag, spaced_flag.join( [ str( tj.id ) for tj in transfer_jobs ] ) )
        log.debug( 'Initiating Transfer Job(s): %s' % ', '.join( [ str( tj.id ) for tj in transfer_jobs ] ) )
        p = subprocess.Popen( cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
        p.wait()
        return p.stdout.read()
    def status( self, transfer_jobs ):
        transfer_jobs = listify( transfer_jobs )
        rval = []
        sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        sock.settimeout( 10 )
        try:
            sock.connect( ( 'localhost', self.tm_port ) )
        except Exception, e:
            log.warning( 'sock.connect for status update of Transfer Jobs %s failed (this is okay if all jobs have finished): %s' % ( ', '.join( [ str( tj.id ) for tj in transfer_jobs ] ), str( e ) ) )
            [ self.sa_session.refresh( tj ) for tj in transfer_jobs ]
            new_jobs = filter( lambda x: x.state == self.app.model.TransferJob.states.NEW, transfer_jobs )
            #terminal_jobs = filter( lambda x: x.state in [ self.app.model.TransferJob.states.DONE, \
            #                                               self.app.model.TransferJob.states.ERROR ], transfer_jobs )
            if new_jobs:
                # This could be a bad idea if the transfer manager daemon is misbehaving.
                output = self.run( new_jobs )
            for tj in transfer_jobs:
                if tj.state == tj.states.DONE:
                    log.debug( 'Transfer Job %s is complete' % tj.id )
                rval.append( dict( transfer_job_id=tj.id, state=tj.state ) )
            if len( rval ) == 1:
                return rval[0]
            return rval
        sock.send( json.to_json_string( dict( state_transfer_job_ids=[ t.id for t in transfer_jobs ] ) ) + '\n' )
        resp = sock.recv( 8192 )
        for line in resp.splitlines():
            status = json.from_json_string( line )
            # TODO: need a bunch for this
            if status['state'] == 'unknown':
                transfer_job = [ tj for tj in transfer_jobs if tj.id == int( status['transfer_job_id'] ) ][0]
                self.sa_session.refresh( tj )
                rval.append( dict( transfer_job_id=tj.id, state=tj.state ) )
            else:
                if status['state'] == 'progress' and 'percent' in status:
                    log.debug( 'Transfer Job %s is %s complete' % ( status['transfer_job_id'], status['percent'] ) )
                rval.append( status )
        if len( rval ) == 1:
            return rval[0]
        return rval
