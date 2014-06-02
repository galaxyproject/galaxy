import logging
import os
import threading

log = logging.getLogger( __name__ )


class AsynchronousReader( threading.Thread ):
    """
    A helper class to implement asynchronous reading of a stream in a separate thread.  Read lines are pushed
    onto a queue to be consumed in another thread.
    """
 
    def __init__( self, fd, queue ):
        threading.Thread.__init__( self )
        self._fd = fd
        self._queue = queue
        self.lines = []
 
    def run( self ):
        """Read lines and put them on the queue."""
        thread_lock = threading.Lock()
        thread_lock.acquire()
        for line in iter( self._fd.readline, '' ):
            stripped_line = line.rstrip()
            self.lines.append( stripped_line )
            self._queue.put( stripped_line )
        thread_lock.release()
 
    def installation_complete( self ):
        """Make sure there is more installation and compilation logging content expected."""
        return not self.is_alive() and self._queue.empty()
