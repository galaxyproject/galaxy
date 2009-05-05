"""
A simple wrapper for writing tarballs as a stream.  The work is performed in a
thread and data is written to a Queue instead of a file.
"""

import logging, tarfile

from Queue import Queue, Empty, Full
from threading import Thread

log = logging.getLogger( __name__ )

class QueueArchive( object ):
    queue_size = 32
    def __init__( self ):
        self.queue = Queue( QueueArchive.queue_size )
        self.get = self.queue.get
        self.empty = self.queue.empty
    def write( self, data ):
        self.queue.put( data, block=True, timeout=300 )
    def tell( self ):
        return 0

class StreamBall( object ):
    def __init__( self, mode, members={} ):
        self.mode = mode
        self.members = members
        self.tarfileobj = QueueArchive()
    def add( self, file, relpath ):
        self.members[file] = relpath
    def stream( self ):
        t = Thread( target=self.thread_write )
        t.start()
        while t.isAlive():
            try:
                yield self.tarfileobj.get( block=False )
            except Empty:
                pass
        t.join()
        # exhaust the queue
        while not self.tarfileobj.empty():
            yield self.tarfileobj.get()
    def thread_write( self ):
        tf = tarfile.open( mode=self.mode, fileobj=self.tarfileobj )
        try:
            for file, rel in self.members.items():
                tf.add( file, arcname=rel )
            tf.close()
        except Full:
            log.warning( 'Queue full for longer than 300 seconds, timing out' )
