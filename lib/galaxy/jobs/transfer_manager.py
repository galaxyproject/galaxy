"""
Client interface to the Galaxy Transfer Manager, which is a standalone,
lightweight on-demand daemon.
"""
import subprocess, socket

from galaxy import eggs
from galaxy.util import listify

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
        cmd = '%s %s %s' % ( self.tm_command, self.tm_transfer_job_id_flag, spaced_flag.join( [ tj.id for tj in transfer_jobs ] ) )
        p = subprocess.Popen( cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        p.wait()
        return p.stderr.read()
    def status( self, transfer_jobs ):
        transfer_jobs = util.listify( transfer_jobs )
        # TODO: timeout, error handling
        rval = []
        sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        try:
            sock.connect( ( 'localhost', self.tm_port ) )
        except:
            log.exception( 'sock.connect for status update failed:' )
            for transfer_job in transfer_jobs:
                self.sa_session.refresh( transfer_job )
                if transfer_job.state in [ self.app.model.TransferJob.states.DONE, \
                                           self.app.model.TransferJob.states.ERROR ]:
                    rval.append( dict( status=transfer_job.state ) )
                else:
                    raise Exception( 'transfer manager not running or responding and transfer job (id: %s) state is non-terminal: %s' % ( transfer_job.id, transfer_job.state ) )
        sock.send( json.to_json_string( dict( status=[ t.id for t in transfer_jobs ] ) ) + '\n' )
        resp = sock.recv( 8192 )
        for line in resp.splitlines():
            status = json.from_json_string( line )
            rval.append( status )
        if len( rval ) == 1:
            return rval[0]
        return rval
