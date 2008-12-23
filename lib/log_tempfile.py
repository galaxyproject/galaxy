# override tempfile methods for debugging

import tempfile, traceback

import logging
log = logging.getLogger( __name__ )

class TempFile( object ):
    def __init__( self ):
        tempfile._NamedTemporaryFile = tempfile.NamedTemporaryFile
        tempfile._mkstemp = tempfile.mkstemp
        tempfile.NamedTemporaryFile = self.NamedTemporaryFile
        tempfile.mkstemp = self.mkstemp
    def NamedTemporaryFile( self, *args, **kwargs ):
        f = tempfile._NamedTemporaryFile( *args, **kwargs )
        try:
            log.debug( ( "Opened tempfile %s with NamedTemporaryFile:\n" % f.name ) + "".join( traceback.format_stack() ) )
        except AttributeError:
            pass
        return f
    def mkstemp( self, *args, **kwargs ):
        f = tempfile._mkstemp( *args, **kwargs )
        try:
            log.debug( ( "Opened tempfile %s with mkstemp:\n" % f[1] ) + "".join( traceback.format_stack() ) )
        except TypeError:
            pass
        return f
