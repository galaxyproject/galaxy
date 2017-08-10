"""
Manage the OpenID consumer and related data stores.
"""

import os
import pickle
import logging

try:
    from openid import oidutil
    from openid.store import filestore
    from openid.consumer import consumer
    from openid.extensions import sreg
except ImportError:
    oidutil = None

    class FakeConsumer( object ):
        def __getattr__(x, y):
            return None
    consumer = FakeConsumer()


OPENID_IMPORT_MESSAGE = ('The Python openid package is required to use this '
                         'feature, please install it')

log = logging.getLogger( __name__ )


def oidlog( message, level=0 ):
    log.debug( message )


if oidutil is not None:
    oidutil.log = oidlog


class OpenIDManager( object ):
    def __init__( self, cache_path ):
        assert oidutil is not None, OPENID_IMPORT_MESSAGE
        self.session_path = os.path.join( cache_path, 'session' )
        self.store_path = os.path.join( cache_path, 'store' )
        for dir in self.session_path, self.store_path:
            if not os.path.exists( dir ):
                os.makedirs( dir )
        self.store = filestore.FileOpenIDStore( self.store_path )

    def get_session( self, trans ):
        session_file = os.path.join( self.session_path, str( trans.galaxy_session.id ) )
        if not os.path.exists( session_file ):
            pickle.dump( dict(), open( session_file, 'w' ) )
        return pickle.load( open( session_file ) )

    def persist_session( self, trans, oidconsumer ):
        session_file = os.path.join( self.session_path, str( trans.galaxy_session.id ) )
        pickle.dump( oidconsumer.session, open( session_file, 'w' ) )

    def get_consumer( self, trans ):
        return consumer.Consumer( self.get_session( trans ), self.store )

    def add_sreg( self, trans, request, required=None, optional=None ):
        if required is None:
            required = []
        if optional is None:
            optional = []
        sreg_request = sreg.SRegRequest( required=required, optional=optional )
        request.addExtension( sreg_request )

    def get_sreg( self, info ):
        return sreg.SRegResponse.fromSuccessResponse( info )

    # so I don't have to expose all of openid.consumer.consumer
    FAILURE = consumer.FAILURE
    SUCCESS = consumer.SUCCESS
    CANCEL = consumer.CANCEL
    SETUP_NEEDED = consumer.SETUP_NEEDED
