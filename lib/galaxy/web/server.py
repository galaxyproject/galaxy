"""
HTTPServer implementation that uses a thread pool based SocketServer (similar
to the approach used by CherryPy) and the WSGIHandler request handler from
Paste. 

Preliminary numbers from "ab -c 50 -n 500 http://localhost:8080/", all tests
with transaction level logging. Application processes a simple cheetah 
template (using compiled NameMapper).

CherryPy 2.1
------------

Percentage of the requests served within a certain time (ms)
  50%    354
  66%    452
  75%    601
  80%    674
  90%   2868
  95%   3000
  98%   3173
  99%   3361
 100%   6145 (last request)
 
Paste with Paste#http server (ThreadingMixIn based)
---------------------------------------------------

Percentage of the requests served within a certain time (ms)
  50%     84
  66%     84
  75%     84
  80%     84
  90%     85
  95%     86
  98%     92
  99%     97
 100%     99 (last request)
 
This module
-----------

Percentage of the requests served within a certain time (ms)
  50%     19
  66%     23
  75%     26
  80%     29
  90%     41
  95%     50
  98%     70
  99%     80
 100%    116 (last request)

"""

import SocketServer
import Queue
import threading
import socket

import logging
log = logging.getLogger( __name__ )

import pkg_resources; 
pkg_resources.require( "Paste" )
from paste.httpserver import WSGIHandler

class ThreadPool( object ):
    """
    Generic thread pool with a queue of callables to consume
    """
    SHUTDOWN = object()
    def __init__( self, nworkers, name="ThreadPool" ):
        """
        Create thread pool with `nworkers` worker threads
        """
        self.nworkers = nworkers
        self.name = name
        self.queue = Queue.Queue()
        self.workers = []
        for i in range( self.nworkers ):
            worker = threading.Thread( target=self.worker_thread_callback, 
                                       name=( "%s worker %d" % ( self.name, i ) ) )
            worker.start()
            self.workers.append( worker )
    def worker_thread_callback( self ):
        """
        Worker thread should call this method to get and process queued 
        callables
        """
        while 1:
            runnable = self.queue.get()
            if runnable is ThreadPool.SHUTDOWN:
                return
            else:
                runnable()
    def shutdown( self ):
        """
        Shutdown the queue (after finishing any pending requests)
        """
        # Add a shutdown request for every worker
        for i in range( self.nworkers ):
            self.queue.put( ThreadPool.SHUTDOWN )
        # Wait for each thread to terminate
        for worker in self.workers:
            worker.join()

class ThreadPoolServer( SocketServer.TCPServer ):
    """
    Server that uses a pool of threads for request handling
    """
    allow_reuse_address = 1
    def __init__( self, server_address, request_handler, nworkers ):
        # Create and start the workers
        self.running = True
        assert nworkers > 0, "ThreadPoolServer must have at least one worker"
        self.thread_pool = ThreadPool( nworkers, "ThreadPoolServer on %s:%d" % server_address )
        # Call the base class constructor
        SocketServer.TCPServer.__init__( self, server_address, request_handler )
    def process_request( self, request, client_address ):
        """
        Queue the request to be processed by on of the thread pool threads
        """
        # This sets the socket to blocking mode (and no timeout) since it
        # may take the thread pool a little while to get back to it. (This
        # is the default but since we set a timeout on the parent socket so
        # that we can trap interrupts we need to restore this,.)
        request.setblocking( 1 )
        # Queue processing of the request
        self.thread_pool.queue.put( lambda: self.process_request_in_thread( request, client_address ) )
    def process_request_in_thread( self, request, client_address ):
        """
        The worker thread should call back here to do the rest of the
        request processing.
        """
        try:
            self.finish_request( request, client_address )
            self.close_request( request)
        except:
            self.handle_error( request, client_address )
            self.close_request( request )            
    def serve_forever(self):
        """
        Overrides `serve_forever` to shutdown cleanly.
        """
        try:
            log.info( "Serving requests..." )
            while self.running:
                try:
                    self.handle_request()
                except socket.timeout:
                    # Timeout is expected, gives interrupts a chance to 
                    # propogate, just keep handling
                    pass
            log.info( "Shutting down..." )
        finally:
            self.thread_pool.shutdown()
    def shutdown( self ):
        """
        Finish pending requests and shutdown the server
        """
        self.running = False
        self.socket.close()
    def server_activate(self):
        """
        Overrides server_activate to set timeout on our listener socket
        """
        # We set the timeout here so that we can trap ^C on windows
        self.socket.settimeout(1)
        SocketServer.TCPServer.server_activate(self)
        
class WSGIThreadPoolServer( ThreadPoolServer ):
    """
    Server that mixes ThreadPoolServer and WSGIHandler
    """
    def __init__( self, wsgi_application, server_address, *args, **kwargs ):
        ThreadPoolServer.__init__( self, server_address, WSGIHandler, *args, **kwargs )
        self.wsgi_application = wsgi_application
        self.wsgi_socket_timeout = None
    def get_request(self):
        # If there is a socket_timeout, set it on the accepted
        (conn,info) = ThreadPoolServer.get_request(self)
        if self.wsgi_socket_timeout:
            conn.settimeout(self.wsgi_socket_timeout)
        return (conn, info)

def serve( wsgi_app, global_conf, host="127.0.0.1", port="8080",
           server_version=None, protocol_version=None, start_loop=True,
           daemon_threads=None, socket_timeout=None, nworkers=10 ):
    """
    Similar to `paste.httpserver.serve` but using the thread pool server
    """
    server_address = ( host, int( port ) )
        
    if server_version:
        handler.server_version = server_version
        handler.sys_version = None
    if protocol_version:
        assert protocol_version in ('HTTP/0.9','HTTP/1.0','HTTP/1.1')
        handler.protocol_version = protocol_version

    server = WSGIThreadPoolServer( wsgi_app, server_address, int( nworkers ) )
    if daemon_threads:
        server.daemon_threads = daemon_threads
    if socket_timeout:
        server.wsgi_socket_timeout = int(socket_timeout)

    print "serving on %s:%s" % server.server_address
    if start_loop:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            # allow CTRL+C to shutdown
            pass
    return server



