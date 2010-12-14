import logging
import galaxy.util
from galaxy.util.odict import odict

class Registry( object ):
    def __init__( self, root_dir=None, config=None ):
        self.log = logging.getLogger( __name__ )
        self.log.addHandler( logging.NullHandler() )
        self.redirect_delay = 2.0 # Default to 2 seconds
        self.sequencer_redirects = odict()
        self.sequencer_requests = []
        self.authentication = None
        if root_dir and config:
            tree = galaxy.util.parse_xml( config )
            root = tree.getroot()
            self.log.debug( 'Loading sequencer actions from %s' % config )
            try:
                # Load the redirect delay value, if any ( default is 2 seconds ).
                for redirect_delay in root.findall( 'redirect_delay' ):
                    delay = redirect_delay.get( 'value', self.redirect_delay )
                    self.redirect_delay = float( delay )
                # Load authentication credentials, if any.
                for authentication_elem in root.findall( 'authentication' ):
                    credentials = authentication_elem.get( 'credentials', '' )
                    if credentials:
                        for request_elem in authentication_elem.findall( 'external_webapp' ):
                            request = request_elem.get( 'request' )
                            if request:
                                self.authentication = ( credentials, request )
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
                    # For now, these should always be complete URLs because they are used to
                    # redirect the window to an external webapp page.  We only use the url from
                    # the resulting tuple of 4 elements, the tuple is built simply to re-use code.
                    self.sequencer_requests.append( self.parse_request_elem( request_elem ) )
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
