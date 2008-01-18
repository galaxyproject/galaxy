"""
A simple WSGI application/framework.
"""

import socket
import types
import logging
import sys

from Cookie import SimpleCookie

import pkg_resources; 
pkg_resources.require( "Paste" )
pkg_resources.require( "Routes" )
pkg_resources.require( "flup" )

import routes

# We will use some very basic HTTP/wsgi utilities from the paste library
from paste.request import parse_headers, get_cookies, parse_formvars
from paste import httpexceptions
from paste.response import HeaderDict

# For FieldStorage
import cgi

log = logging.getLogger( __name__ )

class WebApplication( object ):
    """
    A simple web application which maps requests to objects using routes,
    and to methods on those objects in the CherryPy style. Thus simple 
    argument mapping in the CherryPy style occurs automatically, but more
    complicated encoding of arguments in the PATH_INFO can be performed
    with routes.
    """
    def __init__( self ):
        """
        Create a new web application object. To actually connect some 
        controllers use `add_controller` and `add_route`. Call 
        `finalize_config` when all controllers and routes have been added
        and `__call__` to handle a request (WSGI style). 
        """
        self.controllers = dict()
        self.mapper = routes.Mapper() 
        self.transaction_factory = DefaultWebTransaction
    def add_controller( self, controller_name, controller ):
        """
        Add a controller class to this application. A controller class has
        methods which handle web requests. To connect a URL to a controller's
        method use `add_route`.
        """
        log.debug( "Enabling '%s' controller, class: %s", 
            controller_name, controller.__class__.__name__ )
        self.controllers[ controller_name ] = controller
    def add_route( self, route, **kwargs ):
        """
        Add a route to match a URL with a method. Accepts all keyword
        arguments of `routes.Mapper.connect`. Every route should result in
        at least a controller value which corresponds to one of the 
        objects added with `add_controller`. It optionally may yield an 
        `action` argument which will be used to locate the method to call
        on the controller. Additional arguments will be passed to the
        method as keyword args. 
        """
        self.mapper.connect( route, **kwargs )
    def set_transaction_factory( self, transaction_factory ):
        """
        Use the callable `transaction_factory` to create the transaction
        which will be passed to requests.
        """
        self.transaction_factory = transaction_factory
    def finalize_config( self ):
        """
        Call when application is completely configured and ready to serve
        requests
        """
        # Create/compile the regular expressions for route mapping
        self.mapper.create_regs( self.controllers.keys() )
    def __call__( self, environ, start_response ):
        """
        Call interface as specified by WSGI. Wraps the environment in user
        friendly objects, finds the appropriate method to handle the request
        and calls it.
        """
        # Setup the transaction
        trans = self.transaction_factory( environ )
        # Map url using routes
        path_info = trans.request.path_info
        map = self.mapper.match( path_info )
        if map == None:
            raise httpexceptions.HTTPNotFound( "No route for " + path_info )
        # Save the complete mapper dict, we pop things off so they don't get passed down
        raw_map = dict( map )
        # Get the controller class
        controller_name = map.pop( 'controller', None )
        controller = self.controllers.get( controller_name, None )
        if controller_name is None:
            raise httpexceptions.HTTPNotFound( "No controller for " + path_info )
        # Resolve action method on controller
        action = map.pop( 'action', 'index' )
        method = getattr( controller, action, None )
        if method is None:
            method = getattr( controller, 'default', None )
        if method is None:
            raise httpexceptions.HTTPNotFound( "No action for " + path_info )
        # Is the method exposed
        if not getattr( method, 'exposed', False ): 
            raise httpexceptions.HTTPNotFound( "Action not exposed for " + path_info )
        # Is the method callable
        if not callable( method ):
            raise httpexceptions.HTTPNotFound( "Action not callable for " + path_info ) 
        # Setup routes
        rc = routes.request_config()
        rc.mapper = self.mapper
        rc.mapper_dict = raw_map
        rc.environ = environ
        rc.redirect = trans.response.send_redirect
        # Combine mapper args and query string / form args and call
        kwargs = trans.request.params.mixed()
        kwargs.update( map )
        try:
            body = method( trans, **kwargs )
        except Exception, e:
            body = self.handle_controller_exception( e, trans, **kwargs )
            if not body:
                raise
        # Now figure out what we got back and try to get it to the browser in
        # a smart way
        if callable( body ):
            # Assume the callable is another WSGI application to run
            return body( environ, start_response )
        else:
            start_response( trans.response.wsgi_status(), 
                            trans.response.wsgi_headeritems() )
            if isinstance( body, types.FileType ):
                # Stream the file back to the browser
                return iterate_file( body )
            elif isinstance( body, ( types.GeneratorType, list, tuple ) ):
                # Recursively stream the iterable
                return flatten( body )
            elif isinstance( body, basestring ):
                # Wrap the string so it can be iterated
                return [ body ]
            elif body is None:
                # Returns an empty body
                return []
        # Worst case scenario
        return [ str( body ) ]

    def handle_controller_exception( self, e, trans, **kwargs ):
        """
        Allow handling of exceptions raised in controller methods.
        """
        return False
        
class WSGIEnvironmentProperty( object ):
    """
    Descriptor that delegates a property to a key in the environ member of the
    associated object (provides property style access to keys in the WSGI
    environment)
    """
    def __init__( self, key, default = '' ):
        self.key = key
        self.default = default
    def __get__( self, obj, type = None ):
        if obj is None: return self
        return obj.environ.get( self.key, self.default )

class LazyProperty( object ):
    """
    Property that replaces itself with a calculated value the first time
    it is used.
    """
    def __init__( self, func ):
        self.func = func
    def __get__(self, obj, type = None ):
        if obj is None: return self
        value = self.func( obj )
        setattr( obj, self.func.func_name, value )
        return value
lazy_property = LazyProperty
        
class DefaultWebTransaction( object ):
    """
    Wraps the state of a single web transaction (request/response cycle). 

    TODO: Provide hooks to allow application specific state to be included 
          in here.
    """
    def __init__( self, environ ):
        self.environ = environ
        self.request = Request( environ )
        self.response = Response()
    @lazy_property
    def session( self ):
        """
        Get the user's session state. This is laze since we rarely use it
        and the creation/serialization cost is high.
        """
        if 'com.saddi.service.session' in self.environ:
            return self.environ['com.saddi.service.session'].session
        elif 'beaker.session' in self.environ:
            return self.environ['beaker.session']
        else:
            return None
    
class Request( object ):
    """
    Encapsulates an HTTP request. 
    """
    def __init__( self, environ ):
        """
        Create a new request wrapping the WSGI environment `environ`
        """
        self.environ = environ
    # Properties that are computed and cached on first use
    @lazy_property
    def remote_host( self ):
        try:
            return socket.gethostbyname( self.environ['REMOTE_ADDR'] )
        except socket.error:
            return self.environ['REMOTE_ADDR']
    @lazy_property
    def headers( self ):
        return dict( parse_headers( self.environ ) )
    @lazy_property
    def cookies( self ):
        return get_cookies( self.environ )
    @lazy_property
    def base( self ):
        return ( self.scheme + "://" + self.environ['HTTP_HOST'] )
    @lazy_property
    def params( self ):
        return parse_formvars( self.environ )
    @lazy_property
    def path( self ):
        return self.environ['SCRIPT_NAME'] + self.environ['PATH_INFO']
    @lazy_property
    def browser_url( self ):
        return self.base + self.path        
    # Descriptors that map properties to the associated environment
    scheme = WSGIEnvironmentProperty( 'wsgi.url_scheme' )
    remote_addr = WSGIEnvironmentProperty( 'REMOTE_ADDR' )
    remote_port = WSGIEnvironmentProperty( 'REMOTE_PORT' )
    method = WSGIEnvironmentProperty( 'REQUEST_METHOD' )
    script_name = WSGIEnvironmentProperty( 'SCRIPT_NAME' )
    protocol = WSGIEnvironmentProperty( 'SERVER_PROTOCOL' )
    query_string = WSGIEnvironmentProperty( 'QUERY_STRING' )
    path_info = WSGIEnvironmentProperty( 'PATH_INFO' )
    
class Response( object ):
    """
    Describes an HTTP response. Currently very simple since the actual body
    of the request is handled separately.
    """
    def __init__( self ):
        """
        Create a new Response defaulting to HTML content and "200 OK" status
        """
        self.status = "200 OK"
        self.headers = HeaderDict( { "content-type": "text/html" } )
        self.cookies = SimpleCookie()
    def set_content_type( self, type ):
        """
        Sets the Content-Type header
        """
        self.headers[ "content-type" ] = type
    def send_redirect( self, url ):
        """
        Send an HTTP redirect response to (target `url`)
        """
        raise httpexceptions.HTTPFound( url )
    def wsgi_headeritems( self ):
        """
        Return headers in format appropriate for WSGI `start_response`
        """
        result = self.headers.headeritems()
        # Add cookie to header
        for name in self.cookies.keys():
            crumb = self.cookies[name]
            header, value = str( crumb ).split( ': ', 1 )
            result.append( ( header, value ) )
        return result
    def wsgi_status( self ):
        """
        Return status line in format appropriate for WSGI `start_response`
        """        
        if isinstance( self.status, int ):
            exception = httpexceptions.get_exception( self.status )
            return "%d %s" % ( exception.code, exception.title )
        else:
            return self.status
        
# ---- Utilities ------------------------------------------------------------

CHUNK_SIZE = 2**16

def iterate_file( file ):
    """
    Progressively return chunks from `file`.
    """
    while 1:
        chunk = file.read( CHUNK_SIZE )
        if not chunk:
            break
        yield chunk

def flatten( seq ):
    """
    Flatten a possible nested set of iterables
    """
    for x in seq:
        if isinstance( x, ( types.GeneratorType, list, tuple ) ):
            for y in flatten( x, encoding ):
                yield y
        else:
            yield x