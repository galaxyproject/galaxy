"""
A simple wrapper for writing tarballs as a stream.
"""
import os
import logging
import tarfile
from galaxy.exceptions import ObjectNotFound

log = logging.getLogger( __name__ )


class StreamBall( object ):
    def __init__( self, mode, members=None ):
        self.members = members
        if members is None:
            self.members = {}
        self.mode = mode
        self.wsgi_status = None
        self.wsgi_headeritems = None

    def add( self, file, relpath, check_file=False):
        if check_file and len(file) > 0:
            if not os.path.isfile(file):
                raise ObjectNotFound
            else:
                self.members[file] = relpath
        else:
            self.members[file] = relpath

    def stream( self, environ, start_response ):
        response_write = start_response( self.wsgi_status, self.wsgi_headeritems )

        class tarfileobj:
            def write( self, *args, **kwargs ):
                response_write( *args, **kwargs )
        tf = tarfile.open( mode=self.mode, fileobj=tarfileobj() )
        for file, rel in self.members.items():
            tf.add( file, arcname=rel )
        tf.close()
        return []


class ZipBall(object):
    def __init__(self, tmpf, tmpd):
        self._tmpf = tmpf
        self._tmpd = tmpd

    def stream(self, environ, start_response):
        response_write = start_response( self.wsgi_status, self.wsgi_headeritems )
        tmpfh = open( self._tmpf )
        response_write(tmpfh.read())
        tmpfh.close()
        try:
            os.unlink( self._tmpf )
            os.rmdir( self._tmpd )
        except OSError:
            log.exception( "Unable to remove temporary library download archive and directory" )
        return []
