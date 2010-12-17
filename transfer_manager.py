#!/usr/bin/env python
'''
Manage transfers from sequencers

Design:

    transfer_manager.py configfile <some identifier>

Initialization

    try:
        Open socket
    except:
        try:
            Submit to socket
        except:
            Instruct caller to resubmit (avoids other manager shutting down race condition)

Run

    Needs 2 threads?  One to monitor socket, one to monitor queue.
    Watch the race condition of put into transfer queue after transfer queue is exiting?
    Store queue to db to restart/resume on premature manager termination?

    while len(queue) > 0:
        msg = socket.read()
        if msg == STATUS_REQUEST:
            return state
        elif msg == NEW_DOWNLOAD:
            queue.put( msg )
        
    while queue:
        spawn transfer
        read lines from transfer for progress

'''

import os, sys, optparse, ConfigParser, socket, SocketServer, errno, Queue, threading, subprocess

import urllib2, tempfile

import time

sys.path.insert( 0, os.path.abspath( 'lib' ) )
from galaxy import eggs
import galaxy.model.mapping
from galaxy.util import json, bunch

class ArgHandler( object ):
    """
    Collect command line flags.
    """
    def __init__( self ):
        self.parser = optparse.OptionParser()
        self.parser.add_option( '-c', '--config', dest='config', help='Path to Galaxy config file (universe_wsgi.ini)', default='universe_wsgi.ini' )
        self.parser.add_option( '-i', '--transfer-job-id', action='append', dest='transfer_job_ids', help='Initiate management of the specified TransferJob id' )
        self.parser.add_option( '--do', dest='initiate_transfer_job_id', help='Used by this script when it calls itself to actually initiate the download' )
        self.parser.add_option( '-s', '--state-transfer-job-id', action='append', dest='state_transfer_job_ids', help='Report the state of the specified TransferJob id' )
    def parse():
        opts, args = parser.parse_args()
        if opts.initiate_transfer_job_id is not None:
            opts.initiate_transfer_job_id

class GalaxyApp( object ):
    """
    A shell Galaxy App to provide access to the Galaxy configuration and
    model/database.
    """
    def __init__( self, config_file='universe_wsgi.ini' ):
        self.config = ConfigParser.ConfigParser( dict( database_file = 'database/universe.sqlite',
                                                       file_path = 'database/files',
                                                       transfer_manager_port = 8163 ) )
        self.config.read( config_file )
        self.model = None
    @property
    def sa_session( self ):
        if not self.model:
            default_dburl = 'sqlite:///%s?isolation_level=IMMEDIATE' % self.config.get( 'app:main', 'database_file' )
            try:
                dburl = self.config.get( 'app:main', 'database_connection' )
            except ConfigParser.NoOptionError:
                dburl = default_dburl
            self.model = galaxy.model.mapping.init( self.config.get( 'app:main', 'file_path' ), dburl, create_tables = False )
        return self.model.context.current
    def get_transfer_job( self, id ):
        return self.sa_session.query( self.model.TransferJob ).get( int( id ) )

class ListenerServer( SocketServer.ThreadingTCPServer ):
    """
    The listener will accept state requests and new transfers for as long as
    the manager is running.
    """
    def __init__( self, server_address, RequestHandlerClass, transfer_manager ):
        SocketServer.ThreadingTCPServer.__init__( self, server_address, RequestHandlerClass )
        self.transfer_manager = transfer_manager
        self.app = transfer_manager.app

class ListenerRequestHandler( SocketServer.BaseRequestHandler ):
    """
    Handle state or transfer requests received on the socket.
    """
    def handle( self ):
        if not self.server.transfer_manager.accepting:
            self.request.send( 'Manager shutting down\n' )
            return
        data = ''
        while len( data ) < 8 * 1024 * 1024:
            # read data up to 8MB (overkill, but be safe)
            chunk = self.request.recv( 1024 )
            if not chunk:
                break
            data += chunk
            if '\n' in data:
                break
        else:
            self.request.send( 'Message too large\n' )
            return
        data = json.from_json_string( data )
        if 'transfer_job_ids' in data:
            # Get all of the TransferJob objects and stick them on the queue.
            [ self.server.transfer_manager.transfer_queue.put( self.server.app.get_transfer_job( transfer_job_id ) ) for transfer_job_id in data['transfer_job_ids'] ]
        elif 'state' in data:
            for transfer_id in data['state']:
                self.request.send( '%s %s\n' % ( transfer_id, self.server.transfer_manager.get_state( int( transfer_id ) ) ) )
        self.request.send( 'OK\n' )

class Transfer( object ):
    """
    Instantiated for each transfer to track the progress of the transfer via
    commmunication with a subprocess.
    """
    states = bunch.Bunch( NEW = 'new',
                          UNKNOWN = 'unknown',
                          STARTED = 'started',
                          PROGRESS = 'progress',
                          DONE = 'done' )
    def __init__( self, transfer ):
        self.transfer = transfer
        self.state = dict( state = self.states.NEW )
        self.done = False
    def run( self ):
        cmd = '%s -u %s -d %s' % ( sys.executable, os.path.abspath( __file__ ), self.transfer.id )
        self.p = subprocess.Popen( cmd, bufsize=0, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        line = self.p.stdout.readline()
        while line:
            try:
                self.state = json.from_json_string( line )
                assert 'state' in self.state
            except:
                print 'Received unknown state from transfer (id: %s): %s' % ( transfer.id, line )
                self.state = dict( state=self.states.UNKNOWN
            line = self.p.stdout.readline()
        self.p.wait()
        self.done = True

class TransferManager( object ):
    """
    Manage the queue of transfers, handle the setup of new transfers and
    completion of finished transfers.
    """
    def __init__( self, app, transfer_job_ids ):
        self.app = app
        self.sa_session = app.sa_session
        self.transfer_job_ids = transfer_job_ids
        self.port = app.config.get( 'app:main', 'transfer_manager_port' )
        self.transfer_queue = Queue.Queue()
        self.accepting = True
        self.watchlist = []
        self.listen_or_submit()
    def listen_or_submit( self ):
        """
        The transfer manager is invoked the same way every time, via the
        command line, but if a transfer manager is already running, the new
        manager will simply submit the request to the old manager and
        terminate.
        """
        try:
            self.listener_server = ListenerServer( ( 'localhost', self.port ), ListenerRequestHandler, self )
        except socket.error, e:
            if e[0] == errno.EADDRINUSE:
                self.submit()
                sys.exit()
        self.listener = threading.Thread( target=self.listener_server.serve_forever )
        self.listener.start()

        # Put all the URLs into the queue, additional URLs received before this
        # instance of the manager terminates will also be handled.
        [ self.transfer_queue.put( app.get_transfer_job( tj_id ) ) for tj_id in self.transfer_job_ids ]

        while True:
            # TODO: max transfer limit
            try:
                transfer_job = self.transfer_queue.get_nowait()
                print 'fetching transfer job:', transfer_job.id, 'url is:', transfer_job.params['url']
                t = Transfer( transfer_job )
                tt = threading.Thread( target=t.run )
                tt.start()
                self.watchlist.append( t )
            except Queue.Empty:
                # TODO: this will shutdown the queue as soon the queue is
                # empty, which is almost immediately.  instead, we need to
                # accept until all transfers are finished, then stop accepting,
                # but finish out the queue in case one was added in the instant
                # between empty and no longer accepting.
                # (check the queue one more time after accepting = False)
                if not self.watchlist:
                    self.acecpting = False
                    break
            new_watchlist = []
            for transfer in self.watchlist:
                # TODO: handle failure
                if transfer.done:
                    if transfer.state['state'] == transfer.states.DONE:
                        # TODO: make a bunch for real TransferJob object states.
                        transfer.transfer_job.state = app.model.TransferJob.states.DONE
                        transfer.transfer_job.path = transfer.state['path']
                    else:
                        # TODO: transfer.transfer.info = output or transfer.transfer.params['info'] = output
                        transfer.transfer_job.state = app.model.TransferJob.states.ERROR
                    self.sa_session.add( transfer.transfer_job )
                    self.sa_session.flush()
                else:
                    new_watchlist.append( transfer )
                time.sleep( 1 )
            self.watchlist = new_watchlist
        #except Queue.Empty:
        #    self.accepting = False
        self.listener_server.shutdown()

    def get_state( self, transfer_job_id ):
        rval = None
        for transfer in self.watchlist:
            if transfer.transfer_job.id == transfer_id_job:
                rval = transfer.state
                break
        return rval

    def submit( self ):
        # TODO: can fail if shutdown occurs between failure to bind and submission
        sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        sock.connect( ( 'localhost', self.options.port ) )
        sock.send( json.to_json_string( dict( transfer_job_ids=self.transfer_job_ids ] ) ) + '\n' )
        print sock.recv( 1024 ),
        sock.close()
        sys.exit()

def do_transfer( transfer_job ):
    """
    Actually initiate a transfer (used when the transfer manager calls itself
    with the '--do' flag).
    """
    protocol = transfer_job.params['url'].split( '://' )[0]
    if protocol in ( 'http', 'https' ):
        return do_http_transfer( transfer_job )
    else:
        print >>sys.stderr, 'ERROR: Unsupported protocol: %s' % protocol
        sys.exit( 1 )

def do_http_transfer( transfer_job ):
    """
    "Plugin" for handling http(s) transfers.
    """
    url = transfer_job.params['url']
    f = urllib2.urlopen( url )
    size = f.info().getheader( 'Content-Length' )
    if size is not None:
        size = int( size )
    chunksize = 1024
    read = 0
    last = 0
    fh, fn = tempfile.mkstemp()
    while True:
        chunk = f.read( chunksize )
        if not chunk:
            break
        os.write( fh, chunk )
        if read == 0 and size is None:
            print json.to_json_string( dict( state=Transfer.states.STARTED,
                                             size=None ) ) + '\n'
        elif read == 0:
            print json.to_json_string( dict( state=Transfer.states.STARTED,
                                             size=size ) ) + '\n'
        read += chunksize
        if size is not None and read < size:
            percent = int( float( read ) / size * 100 )
            if percent != last:
                print json.to_json_string( dict( state=Transfer.states.PROGRESS,
                                                 percent='%s%%' % percent ) ) + '\n'
                last = percent
        time.sleep( 1 )
    os.close( fh )
    print json.to_json_string( dict( state=Transfer.states.DONE, path=fn ) ) + '\n'

def request_state( transfer_job_ids, port ):
    sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
    sock.connect( ( 'localhost', port ) )
    sock.send( json.to_json_string( dict( state=transfer_job_ids ) ) + '\n' )
    print sock.recv( 1024 ),
    sock.close()
    sys.exit()

if __name__ == '__main__':
    arg_handler = ArgHandler()
    app = GalaxyApp()
    opts, args = arg_handler.parse()
    if opts.initiate_transfer_job_id is not None:
        do_transfer( app.get_transfer_job( opts.initiate_transfer_job_id ) )
    elif opts.state_transfer_job_ids:
        request_state( opts.state_transfer_job_ids, app.config.get( 'app:main', 'transfer_manager_port' ) )
    elif opts.transfer_job_ids:
        transfer_manager = TransferManager( app, opts.transfer_job_ids )
    else:
        arg_handler.parser.print_usage( sys.stderr )
        sys.exit( 1 )
