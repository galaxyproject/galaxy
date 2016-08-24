"""
Batch API middleware

Adds a single route to the installation that:
  1. accepts a POST call containing a JSON array of 'http-like' JSON
     dictionaries.
  2. Each dictionary describes a single API call within the batch and is routed
     back by the middleware to the application's `handle_request` as if it was
     a separate request.
  3. Each response generated is combined into a final JSON list that is
     returned from the POST call.

In this way, API calls can be kept properly atomic and the endpoint can compose
them into complex tasks using only one request.

..note: This batch system is primarily designed for use by the UI as these
types of batch operations *reduce the number of requests* for a given group of
API tasks. IOW, this ain't about batching jobs.

..warning: this endpoint is experimental is likely to change.
"""
import io
from urlparse import urlparse
import json
import re

from paste import httpexceptions
import routes

import logging
log = logging.getLogger( __name__ )


class BatchMiddleware( object ):
    """
    Adds a URL endpoint for processing batch API calls formatted as a JSON
    array of JSON dictionaries. These dictionaries are in the form:
    [
        {
            "url": "/api/histories",
            "type": "POST",
            "body": "{ \"name\": \"New History Name\" }"
        },
        ...
    ]

    where:
      * `url` is the url for the API call to be made including any query string
      * `type` is the HTTP method used (e.g. 'POST', 'PUT') - defaults to 'GET'
      * `body` is the text body of the request (optional)
      * `contentType` content-type request header (defaults to application/json)
    """
    DEFAULT_CONFIG = {
        'route' : '/api/batch',
        'allowed_routes' : [
            '^api\/users.*',
            '^api\/histories.*',
            '^api\/jobs.*',
        ]
    }

    def __init__( self, galaxy, application, config=None ):
        #: the original galaxy webapp
        self.galaxy = galaxy
        #: the wrapped webapp
        self.application = application
        self.config = self.DEFAULT_CONFIG.copy()
        self.config.update( config )
        self.base_url = routes.url_for( '/' )
        self.handle_request = self.galaxy.handle_request

    def __call__( self, environ, start_response ):
        if environ[ 'PATH_INFO' ] == self.config[ 'route' ]:
            return self.process_batch_requests( environ, start_response )
        return self.application( environ, start_response )

    def process_batch_requests( self, batch_environ, start_response ):
        """
        Loops through any provided JSON formatted 'requests', aggregates their
        JSON responses, and wraps them in the batch call response.
        """
        payload = self._read_post_payload( batch_environ )
        requests = payload.get( 'batch', [] )

        responses = []
        for request in requests:
            if not self._is_allowed_route( request[ 'url' ] ):
                responses.append( self._disallowed_route_response( request[ 'url' ] ) )
                continue

            request_environ = self._build_request_environ( batch_environ, request )
            response = self._process_batch_request( request, request_environ, start_response )
            responses.append( response )

        batch_response_body = json.dumps( responses )
        start_response( '200 OK', [
            ( 'Content-Length', len( batch_response_body ) ),
            ( 'Content-Type', 'application/json' ),
        ])
        return batch_response_body

    def _read_post_payload( self, environ ):
        request_body_size = int( environ.get( 'CONTENT_LENGTH', 0 ) )
        request_body = environ[ 'wsgi.input' ].read( request_body_size ) or '{}'
        # TODO: json decode error handling
        # log.debug( 'request_body: (%s)\n%s', type( request_body ), request_body )
        payload = json.loads( request_body )
        return payload

    def _is_allowed_route( self, route ):
        if self.config.get( 'allowed_routes', None ):
            shortened_route = route.replace( self.base_url, '', 1 )
            matches = [ re.match( allowed, shortened_route ) for allowed in self.config[ 'allowed_routes' ] ]
            return any( matches )
        return True

    def _disallowed_route_response( self, route ):
        return dict( status=403, headers=self._default_headers(), body={
            'err_msg'   : 'Disallowed route used for batch operation',
            'route'     : route,
            'allowed'   : self.config[ 'allowed_routes' ]
        })

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

        request_body = request.get( 'body', u'' )
        # set this to None so webob/request will copy the body using the raw bytes
        # if we set it, webob will try to use the buffer interface on a unicode string
        request_environ[ 'CONTENT_LENGTH' ] = None
        # this may well need to change in py3
        request_body = io.BytesIO( bytearray( request_body, encoding='utf8' ) )
        request_environ[ 'wsgi.input' ] = request_body
        # log.debug( 'request_environ:\n%s', pprint.pformat( request_environ ) )

        return request_environ

    def _process_batch_request( self, request, environ, start_response ):
        # We may need to include middleware to record various reponses, but this way of doing that won't work:
        # status, headers, body = self.application( environ, start_response, body_renderer=self.body_renderer )

        # We have to re-create the handle request method here in order to bypass reusing the 'api/batch' request
        #   because reuse will cause the paste error:
        # File "./eggs/Paste-1.7.5.1-py2.7.egg/paste/httpserver.py", line 166, in wsgi_start_response
        #     assert 0, "Attempt to set headers a second time w/o an exc_info"
        try:
            response = self.galaxy.handle_request( environ, start_response, body_renderer=self.body_renderer )
        # handle errors from galaxy.handle_request (only 404s)
        except httpexceptions.HTTPNotFound:
            response = dict( status=404, headers=self._default_headers(), body={} )
        return response

    def body_renderer( self, trans, body, environ, start_response ):
        # this is a dummy renderer that does not call start_response
        # See 'We have to re-create the handle request method...' in _process_batch_request above
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
