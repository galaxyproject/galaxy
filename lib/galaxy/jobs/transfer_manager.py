"""
Manage transfers from arbitrary URLs to temporary files.  Socket interface for
IPC with multiple process configurations.
"""
import json
import logging
import os
import socket
import subprocess
import threading

from galaxy.util import listify, sleeper
from galaxy.util.json import jsonrpc_request, validate_jsonrpc_response

log = logging.getLogger( __name__ )


class TransferManager( object ):
    """
    Manage simple data transfers from URLs to temporary locations.
    """
    def __init__( self, app ):
        self.app = app
        self.sa_session = app.model.context.current
        self.command = 'python %s' % os.path.abspath( os.path.join( os.getcwd(), 'scripts', 'transfer.py' ) )
        if app.config.get_bool( 'enable_job_recovery', True ):
            # Only one Galaxy server process should be able to recover jobs! (otherwise you'll have nasty race conditions)
            self.running = True
            self.sleeper = sleeper.Sleeper()
            self.restarter = threading.Thread( target=self.__restarter )
            self.restarter.start()

    def new( self, path=None, **kwd ):
        if 'protocol' not in kwd:
            raise Exception( 'Missing required parameter "protocol".' )
        protocol = kwd[ 'protocol' ]
        if protocol in [ 'http', 'https' ]:
            if 'url' not in kwd:
                raise Exception( 'Missing required parameter "url".' )
        elif protocol == 'scp':
            # TODO: add more checks here?
            if 'sample_dataset_id' not in kwd:
                raise Exception( 'Missing required parameter "sample_dataset_id".' )
            if 'file_path' not in kwd:
                raise Exception( 'Missing required parameter "file_path".' )
        transfer_job = self.app.model.TransferJob( state=self.app.model.TransferJob.states.NEW, params=kwd )
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
        transfer_jobs = listify( transfer_jobs )
        printable_tj_ids = ', '.join( [ str( tj.id ) for tj in transfer_jobs ] )
        log.debug( 'Initiating transfer job(s): %s' % printable_tj_ids )
        # Set all jobs running before spawning, or else updating the state may
        # clobber a state change performed by the worker.
        [ tj.__setattr__( 'state', tj.states.RUNNING ) for tj in transfer_jobs ]
        self.sa_session.add_all( transfer_jobs )
        self.sa_session.flush()
        for tj in transfer_jobs:
            # The transfer script should daemonize fairly quickly - if this is
            # not the case, this process will need to be moved to a
            # non-blocking method.
            cmd = '%s %s' % ( self.command, tj.id )
            log.debug( 'Transfer command is: %s' % cmd )
            p = subprocess.Popen( cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
            p.wait()
            output = p.stdout.read( 32768 )
            if p.returncode != 0:
                log.error( 'Spawning transfer job failed: %s: %s' % ( tj.id, output ) )
                tj.state = tj.states.ERROR
                tj.info = 'Spawning transfer job failed: %s' % output.splitlines()[-1]
                self.sa_session.add( tj )
                self.sa_session.flush()

    def get_state( self, transfer_jobs, via_socket=False ):
        transfer_jobs = listify( transfer_jobs )
        rval = []
        for tj in transfer_jobs:
            if via_socket and tj.state not in tj.terminal_states and tj.socket:
                try:
                    request = jsonrpc_request( method='get_state', id=True )
                    sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
                    sock.settimeout( 5 )
                    sock.connect( ( 'localhost', tj.socket ) )
                    sock.send( json.dumps( request ) )
                    response = sock.recv( 8192 )
                    valid, response = validate_jsonrpc_response( response, id=request['id'] )
                    if not valid:
                        # No valid response received, make some pseudo-json-rpc
                        raise Exception( dict( code=128, message='Did not receive valid response from transfer daemon for state' ) )
                    if 'error' in response:
                        # Response was valid but Request resulted in an error
                        raise Exception( response['error'])
                    else:
                        # Request was valid
                        response['result']['transfer_job_id'] = tj.id
                        rval.append( response['result'] )
                except Exception as e:
                    # State checking via the transfer daemon failed, just
                    # return the state from the database instead.  Callers can
                    # look for the 'error' member of the response to see why
                    # the check failed.
                    self.sa_session.refresh( tj )
                    error = e.args
                    if type( error ) != dict:
                        error = dict( code=256, message='Error connecting to transfer daemon', data=str( e ) )
                    rval.append( dict( transfer_job_id=tj.id, state=tj.state, error=error ) )
            else:
                self.sa_session.refresh( tj )
                rval.append( dict( transfer_job_id=tj.id, state=tj.state ) )
        for tj_state in rval:
            if tj_state['state'] in self.app.model.TransferJob.terminal_states:
                log.debug( 'Transfer job %s is in terminal state: %s' % ( tj_state['transfer_job_id'], tj_state['state'] ) )
            elif tj_state['state'] == self.app.model.TransferJob.states.PROGRESS and 'percent' in tj_state:
                log.debug( 'Transfer job %s is %s%% complete' % ( tj_state[ 'transfer_job_id' ], tj_state[ 'percent' ] ) )
        if len( rval ) == 1:
            return rval[0]
        return rval

    def __restarter( self ):
        log.info( 'Transfer job restarter starting up...' )
        while self.running:
            dead = []
            self.sa_session.expunge_all()  # our session is threadlocal so this is safe.
            for tj in self.sa_session.query( self.app.model.TransferJob ) \
                          .filter( self.app.model.TransferJob.state == self.app.model.TransferJob.states.RUNNING ):
                if not tj.pid:
                    continue
                # This will only succeed if the process exists and is owned by the
                # user running Galaxy (unless that user is root, in which case it
                # can be owned by anyone - but you're not running Galaxy as root,
                # right?).  This is not guaranteed proof that the transfer is alive
                # since another process may have assumed the original process' PID.
                # But that will only cause the transfer to not restart until that
                # process dies, which hopefully won't be too long from now...  If
                # it becomes a problem, try to talk to the socket a few times and
                # restart the transfer if socket communication fails repeatedly.
                try:
                    os.kill( tj.pid, 0 )
                except:
                    self.sa_session.refresh( tj )
                    if tj.state == tj.states.RUNNING:
                        log.error( 'Transfer job %s is marked as running but pid %s appears to be dead.' % ( tj.id, tj.pid ) )
                        dead.append( tj )
            if dead:
                self.run( dead )
            self.sleeper.sleep( 30 )
        log.info( 'Transfer job restarter shutting down...' )

    def shutdown( self ):
        self.running = False
        self.sleeper.wake()
