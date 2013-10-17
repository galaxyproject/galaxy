import logging
import galaxy.util
from galaxy.util.odict import odict

class Registry( object ):
    def __init__( self, root_dir=None, config=None ):
        self.log = logging.getLogger( __name__ )
        self.log.addHandler( logging.NullHandler() )
        self.redirect_delay = 2.0 # Default to 2 seconds
        self.final_redirect = []
        self.sequencer_redirects = odict()
        self.sequencer_requests = []
        self.authenticated = False
        self.browser_login = None
        self.http_headers_authorization = None
        self.basic_http_authentication = None
        self.http_cookie_processor_authentication = None
        if root_dir and config:
            tree = galaxy.util.parse_xml( config )
            root = tree.getroot()
            self.log.debug( 'Loading sequencer actions from %s' % config )
            try:
                # Load the redirect delay value, if any ( default is 2 seconds ).
                for redirect_delay in root.findall( 'redirect_delay' ):
                    delay = redirect_delay.get( 'value', self.redirect_delay )
                    self.redirect_delay = float( delay )
                # Load http_headers_authorization information, if any.
                for authentication_elem in root.findall( 'http_headers_authorization' ):
                    # Example tag:
                    # <http_headers_authorization credentials="administrator:galaxy" url="http://127.0.0.1" />
                    url = authentication_elem.get( 'url', '' )
                    credentials = authentication_elem.get( 'credentials', '' )
                    self.http_headers_authorization = ( url, credentials )
                # Load basic_http_authentication information, if any.
                for authentication_elem in root.findall( 'basic_http_authentication' ):
                    # Example tag:
                    # <basic_http_authentication user="administrator" password="galaxy" url="http://127.0.0.1" realm="" />
                    urls = []
                    user = authentication_elem.get( 'user', '' )
                    password = authentication_elem.get( 'password', '' )
                    url = authentication_elem.get( 'url', '' )
                    realm = authentication_elem.get( 'realm', '' )
                    self.basic_http_authentication.append( ( user, password, url, realm ) )
                # Load http_cookie_processor_authentication information, if any.
                for authentication_elem in root.findall( 'http_cookie_processor_authentication' ):
                    # Example tag:
                    # <http_cookie_processor_authentication url="http://127.0.0.1/login">
                    #    <param name="user" value="administrator"/>
                    #    <param name="password" value="galaxy"/>
                    # </http_cookie_processor_authentication>
                    url = authentication_elem.get( 'url', None )
                    if url:
                        # Include parameters, if any
                        params = {}
                        for param_elem in authentication_elem.findall( 'param' ):
                            param_name = param_elem.get( 'name' )
                            param_value = param_elem.get( 'value' )
                            params[ param_name ] = param_value
                        self.http_cookie_processor_authentication = dict( url=url, params=params )
                # Load browser_login information, if any.
                for authentication_elem in root.findall( 'browser_login' ):
                    url = authentication_elem.get( 'url', None )
                    if url:
                        # Include parameters, if any
                        params = {}
                        for param_elem in authentication_elem.findall( 'param' ):
                            param_name = param_elem.get( 'name' )
                            param_value = param_elem.get( 'value' )
                            params[ param_name ] = param_value
                        self.browser_login = dict( url=url, params=params )
                # Load redirects
                for redirect_elem in root.findall( 'redirect' ):
                    requests = []
                    action_dict = {}
                    action_dict[ 'title' ] = redirect_elem.get( 'title', None )
                    action = redirect_elem.get( 'action', None )
                    # Load the external webapp requests, if any exist for this redirect action
                    for request_elem in redirect_elem.findall( 'external_webapp' ):
                        requests.append( self.parse_request_elem( request_elem ) )
                    if requests:
                        action_dict[ 'requests' ] = requests
                    self.sequencer_redirects[ action ] = action_dict
                # Load the external webapp requests, if any exist for the sequencer action
                for request_elem in root.findall( 'external_webapp' ):
                    self.sequencer_requests.append( self.parse_request_elem( request_elem ) )
                # Load the special final redirect, used to redirect the browser to defined URL.
                for request_elem in root.findall( 'final_redirect' ):
                    self.final_redirect.append( self.parse_request_elem( request_elem ) )
            except Exception, e:
                self.log.debug( 'Error loading sequencer action: %s' % str( e ) )
        # Default values
        if not self.sequencer_redirects:
            self.sequencer_redirects[ 'start_run' ] = dict( title = 'Start run' )
            self.sequencer_redirects[ 'run_finished' ] = dict( title = 'Run finished' )
    def parse_request_elem( self, request_elem ):
        request = request_elem.get( 'request', None )
        # Get the http method, default is get
        http_method = request_elem.get( 'http_method', 'get' )
        # Include request parameters, if any
        params = {}
        for param_elem in request_elem.findall( 'param' ):
            param_name = param_elem.get( 'name' )
            param_value = param_elem.get( 'value' )
            params[ param_name ] = param_value
        # Handle response, if any ( there should only be 0 or 1 ).
        response_type = None
        for response_elem in request_elem.findall( 'response' ):
            response_type = response_elem.get( 'type', None )
        return ( request, http_method, params, response_type )
