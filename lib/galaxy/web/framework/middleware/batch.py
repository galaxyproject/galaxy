"""
"""

import StringIO
from urlparse import urlparse
import simplejson as json

import pkg_resources
pkg_resources.require( "Paste" )
from paste import httpexceptions

import pprint

import logging
log = logging.getLogger( __name__ )


class BatchMiddleware(object):
    """
    """
    DEFAULT_CONFIG = {
        'route' : '/api/batch'
    }
    # TODO: whitelist or blacklisted urls

    def __init__( self, galaxy, application, config=None ):
        #: the original galaxy webapp
        self.galaxy = galaxy
        #: the wrapped webapp
        self.application = application
        self.config = config or self.DEFAULT_CONFIG
        self.handle_request = self.galaxy.handle_request

    def __call__( self, environ, start_response ):
        if environ[ 'PATH_INFO' ] == self.config[ 'route' ]:
            return self.process_batch_requests( environ, start_response )
        return self.application( environ, start_response )

    def process_batch_requests( self, batch_environ, start_response ):
        # log.debug( ( '=' * 40 ) )
        # log.debug( 'BATCH_REQUEST' )

        payload = self._read_post_payload( batch_environ )
        requests = payload.get( 'batch', [] )
        responses = []
        for request in requests:
            if not self._valid( request ):
                continue

            # log.debug( ( '-' * 40 ) + 'REQUEST BEGIN' )
            request_environ = self._build_request_environ( batch_environ, request )
            # log.debug( 'request: %s', request )
            responses.append( self._proccess_batch_request( request, request_environ, start_response ) )
            # log.debug( ( '-' * 40 ) + 'END' )

        # log.debug( 'batch_response_body: %s', pprint.pformat( responses ) )
        batch_response_body = json.dumps( responses )
        start_response( '200 OK', [
            ( 'Content-Length', len( batch_response_body ) ),
            ( 'Content-Type', 'application/json' ),
        ])
        # log.debug( ( '=' * 40 ) )
        return batch_response_body

    def _valid( self, request ):
        return True

    def _read_post_payload( self, environ ):
        request_body_size = int( environ.get( 'CONTENT_LENGTH', 0 ) )
        request_body = environ[ 'wsgi.input' ].read( request_body_size ) or '{}'
        # TODO: json decode error handling
        # log.debug( 'request_body: (%s)\n%s', type( request_body ), request_body )
        payload = json.loads( request_body )
        return payload

    def _build_request_environ( self, original_environ, request ):
        """
        Given a request and the original environ used to call the batch, return
        a new environ parsable/suitable for the individual api call.
        """
        # TODO: use a dict of defaults/config
        # copy the original environ and reconstruct a fake version for each batched request
        request_environ = original_environ.copy()
        # TODO: for now, do not overwrite the other headers used in the main api/batch request
        request_environ[ 'CONTENT_TYPE' ] = request.get( 'contentType', 'application/json' )
        request_environ[ 'REQUEST_METHOD' ] = request.get( 'method', request.get( 'type', 'GET' ) )
        url = '{0}://{1}{2}'.format( request_environ.get( 'wsgi.url_scheme' ),
                                     request_environ.get( 'HTTP_HOST' ),
                                     request[ 'url' ] )
        parsed = urlparse( url )
        request_environ[ 'PATH_INFO' ] = parsed.path
        request_environ[ 'QUERY_STRING' ] = parsed.query
        request_environ[ 'wsgi.input' ] = StringIO.StringIO( request.get( 'body', '' ) )

        # log.debug( 'request_environ:\n%s', pprint.pformat( request_environ ) )
        return request_environ

    def _proccess_batch_request( self, request, environ, start_response ):
        # log.debug( ( '.' * 40 ) )

        # We may need to include middleware to record various reponses, but this way of doing that won't work:
        # status, headers, body = self.application( environ, start_response, body_renderer=self.body_renderer )

        # We have to re-create the handle request method here in order to bypass reusing the 'api/batch' request
        #   because reuse will cause the paste error:
        # File "/Users/carleberhard/galaxy/api-v2/eggs/Paste-1.7.5.1-py2.7.egg/paste/httpserver.py", line 166, in wsgi_start_response
        #     assert 0, "Attempt to set headers a second time w/o an exc_info"
        try:
            response = self.galaxy.handle_request( environ, start_response, body_renderer=self.body_renderer )
        # handle errors from galaxy.handle_request (only 404s)
        except httpexceptions.HTTPNotFound:
            response = dict( status=404, headers=self._default_headers(), body={} )
        return response
        # log.debug( ( '.' * 40 ) )

    def body_renderer( self, trans, body, environ, start_response ):
        # this is a dummy renderer that does not call start_response
        return dict(
            status=trans.response.status,
            headers=trans.response.headers,
            body=json.loads( self.galaxy.make_body_iterable( trans, body )[0] )
        )

    def _default_headers( self ):
        return {
            'x-frame-options': 'SAMEORIGIN',
            'content-type'   : 'application/json',
            'cache-control'  : 'max-age=0,no-cache,no-store'
        }

    def handle_exception( self, environ ):
        return False
