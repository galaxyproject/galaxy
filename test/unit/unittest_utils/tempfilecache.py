import logging
import os
import tempfile

logging.getLogger( __name__ )
log = logging


class TempFileCache( object ):
    """
    Creates and caches tempfiles with/based-on the given contents.
    """

    def __init__( self, logger=None ):
        if logger:
            global log
            log = logger
        super( TempFileCache, self ).__init__()
        self.clear()

    def clear( self ):
        self.delete_tmpfiles()
        self._content_dict = {}

    def create_tmpfile( self, contents ):
        if not hasattr( self, '_content_dict' ):
            self.set_up_tmpfiles()

        if contents not in self._content_dict:
            # create a named tmp and write contents to it, return filename
            tmpfile = tempfile.NamedTemporaryFile( delete=False )
            tmpfile.write( contents )
            tmpfile.close()
            log.debug( 'created tmpfile.name: %s', tmpfile.name )
            self._content_dict[ contents ] = tmpfile.name

        else:
            log.debug( '(cached): %s', self._content_dict[ contents ] )
        return self._content_dict[ contents ]

    def delete_tmpfiles( self ):
        if not hasattr( self, '_content_dict' ) or not self._content_dict:
            return
        for tmpfile_contents in self._content_dict:
            tmpfile = self._content_dict[ tmpfile_contents ]
            if os.path.exists( tmpfile ):
                log.debug( 'unlinking tmpfile: %s', tmpfile )
                os.unlink( tmpfile )
