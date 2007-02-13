"""
HTTPServer implementation that uses a thread pool based SocketServer (similar
to the approach used by CherryPy) and the WSGIHandler request handler from
Paste. 
"""

import SocketServer
import Queue
import threading
import thread
import sys
import socket
import select
import os
import signal
import errno

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
        self.worker_tracker = {}
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
                self.worker_tracker[thread.get_ident()] = [None, None]
                try:
                    runnable()
                finally:
                    try:
                        del self.worker_tracker[thread.get_ident()]
                    except KeyError:
                        pass
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

class PreforkThreadPoolServer( SocketServer.TCPServer ):
    """
    Server that uses a pool of threads for request handling
    """
    allow_reuse_address = 1
    def __init__( self, server_address, request_handler, nworkers, nprocesses ):
        # Create and start the workers
        self.nprocesses = nprocesses
        self.nworkers = nworkers
        self.running = True
        assert nworkers > 0, "ThreadPoolServer must have at least one worker"
        # Call the base class constructor
        SocketServer.TCPServer.__init__( self, server_address, request_handler )
        
    def get_request( self ):
        self.socket_lock.acquire()
        try:
            return self.socket.accept()
        finally:
            self.socket_lock.release()
        
    def serve_forever(self):
        """
        Overrides `serve_forever` to shutdown cleanly.
        """
        log.info( "Serving requests..." )
        # Pre-fork each child
        children = []
        for i in range( self.nprocesses ):
            pid = os.fork()
            if pid:
                # We are in the parent process
                children.append( pid )
            else:
                # We are in the child process
                signal.signal( signal.SIGINT, self.child_sigint_handler )
                self.time_to_terminate = threading.Event()
                self.socket_lock = threading.Lock()
                self.pid = os.getpid()
                self.serve_forever_child()
                sys.exit( 0 )
        # Wait
        try:
            while len( children ) > 0:
                pid, status = os.wait()
                children.remove( pid )
        except KeyboardInterrupt:
            # Cleanup, kill all children
            print "Killing Children"
            for child in children:
                os.kill( child, signal.SIGINT )
            # Setup and alarm for 10 seconds
            signal.signal( signal.SIGALRM, lambda x, y: None )
            signal.alarm( 10 )
            # Wait
            while len( children ) > 0:
                try:
                    pid, status = os.wait()
                    children.remove( pid )
                except OSError, e:
                    if e[0] in (errno.ECHILD, errno.EINTR):
                        break
            # Kill any left
            print "Killing"
            for child in children:
                os.kill( child, signal.SIGKILL )
        log.info( "Shutting down..." )
        
    def serve_forever_child( self ):
        # self.thread_pool = ThreadPool( self.nworkers, "ThreadPoolServer on %s:%d" % self.server_address )
        self.workers = []
        for i in range( self.nworkers ):
            worker = threading.Thread( target=self.serve_forever_thread )
            worker.start()
            self.workers.append( worker )
        self.time_to_terminate.wait()
        print "Terminating"
        for thread in self.workers:
            thread.join()
        self.socket.close()
            
    def serve_forever_thread( self ):
        while self.running:
            self.handle_request()
            
    def child_sigint_handler( self, signum, frame ):
        print "Shutting down child"
        self.shutdown()
            
    def shutdown( self ):
        """
        Finish pending requests and shutdown the server
        """
        self.running = False
        self.time_to_terminate.set()
        
    ## def server_activate(self):
    ##     """
    ##     Overrides server_activate to set timeout on our listener socket
    ##     """
    ##     # We set the timeout here so that we can trap ^C on windows
    ##     self.socket.settimeout(1)
    ##     SocketServer.TCPServer.server_activate(self)
        
class WSGIPreforkThreadPoolServer( PreforkThreadPoolServer ):
    """
    Server that mixes ThreadPoolServer and WSGIHandler
    """
    def __init__( self, wsgi_application, server_address, *args, **kwargs ):
        PreforkThreadPoolServer.__init__( self, server_address, WSGIHandler, *args, **kwargs )
        self.wsgi_application = wsgi_application
        self.wsgi_socket_timeout = None
    def get_request(self):
        # If there is a socket_timeout, set it on the accepted
        (conn,info) = PreforkThreadPoolServer.get_request(self)
        if self.wsgi_socket_timeout:
            conn.settimeout(self.wsgi_socket_timeout)
        return (conn, info)





def serve( wsgi_app, global_conf, host="127.0.0.1", port="8080",
           server_version=None, protocol_version=None, start_loop=True,
           daemon_threads=None, socket_timeout=None, nworkers=10, nprocesses=10 ):
    """
    Similar to `paste.httpserver.serve` but using the thread pool server
    """
    server_address = ( host, int( port ) )

    # if server_version:
    #     handler.server_version = server_version
    #     handler.sys_version = None
    # if protocol_version:
    #     assert protocol_version in ('HTTP/0.9','HTTP/1.0','HTTP/1.1')
    #     handler.protocol_version = protocol_version

    server = WSGIPreforkThreadPoolServer( wsgi_app, server_address, int( nworkers ), int( nprocesses ) )
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

if __name__ == '__main__':
    from paste.wsgilib import dump_environ
    serve(dump_environ, {}, server_version="Wombles/1.0",
          protocol_version="HTTP/1.1", port="8881")
