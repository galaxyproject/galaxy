from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago
from galaxy import util
import time, socket, urllib, urllib2, base64
from galaxy.util.json import *
from urllib import quote_plus, unquote_plus

import logging
log = logging.getLogger( __name__ )

class CommonController( BaseController ):
    @web.expose
    def index( self, trans, **kwd ):
        redirect_action = util.restore_text( kwd.get( 'redirect_action', '' ) )
        title = util.restore_text( kwd.get( 'title', '' ) )
        JobId = util.restore_text( kwd.get( 'JobId', '' ) )
        sample_id = util.restore_text( kwd.get( 'sample_id', '' ) )
        field_0 = util.restore_text( kwd.get( 'field_0', '' ) )
        message = util.restore_text( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        redirect_delay = trans.app.sequencer_actions_registry.redirect_delay
        # FIXME: this doesn't work, and the user is currently forced to login manually
        #sequencer_authentication = trans.app.sequencer_actions_registry.authentication
        #if sequencer_authentication:
        #    # Login the defined user
        #    credentials, request = sequencer_authentication
        #    req = urllib2.Request( request )
        #    req.add_header( 'Authorization', base64.b64encode( credentials ) )
        sequencer_redirects = trans.app.sequencer_actions_registry.sequencer_redirects
        sequencer_requests = trans.app.sequencer_actions_registry.sequencer_requests
        requests = []
        if redirect_action == 'stop':
            for request_tup in sequencer_requests:
                # Hack: this currently only allows for a single sequencer request since we are redirecting.
                # We only use the url from the tuple of 4 elements, the tuple is built simply to re-use code.
                url, http_method, request_params, response_type = self.parse_request_tup( request_tup, **kwd )
                return trans.fill_template( 'webapps/demo_sequencer/redirect.mako', redirect_url=url )
            # Exit if we have no redirection
            redirect_action = 'exit'
        elif not redirect_action:
            redirect_action, action_dict = sequencer_redirects.items()[0]
            title = action_dict[ 'title' ]
            if 'requests' in action_dict:
                requests = action_dict[ 'requests' ]
        else:
            for index, key in enumerate( sequencer_redirects.iterkeys() ):
                if redirect_action == key:
                    try:
                        # Move to the next action, if there is one.
                        redirect_action = sequencer_redirects.keys()[ index + 1 ]
                        action_dict = sequencer_redirects[ redirect_action ]
                        title = action_dict[ 'title' ]
                    except:
                        # Keep displaying the same title on the page until we redirect ( if we do ).
                        action_dict = sequencer_redirects[ redirect_action ]
                        title = action_dict[ 'title' ]
                        # If we're done redirecting, stop.
                        redirect_action = 'stop'
                    break
        # Handle requests, if there are any
        for request_tup in requests:
            url, http_method, request_params, response_type = self.parse_request_tup( request_tup, **kwd )
            response = self.handle_request( trans, url, http_method, **request_params )
            # Handle response, currently only handles json
            if response_type == 'json':
                response = from_json_string( response )
                # Handle response that is an error, for example:
                # { "Success":false, "Message":"some error string" }
                if 'Success' in response and response[ 'Success' ] == 'false':
                    message = response[ 'Message' ]
                    return self.handle_failure( trans, url, message )
                if 'JobId' in response:
                    JobId = str( response[ 'JobId' ] )
                    kwd[ 'JobId' ] = JobId
        time.sleep( redirect_delay )
        return trans.fill_template( "webapps/demo_sequencer/index.mako",
                                    redirect_action=redirect_action,
                                    title=title,
                                    sample_id=sample_id,
                                    field_0=field_0,
                                    JobId=JobId,
                                    message=message,
                                    status=status )
    def parse_request_tup( self, request_tup, **kwd ):
        redirect_action = util.restore_text( kwd.get( 'redirect_action', '' ) )
        title = util.restore_text( kwd.get( 'title', '' ) )
        JobId = util.restore_text( kwd.get( 'JobId', '' ) )
        sample_id = util.restore_text( kwd.get( 'sample_id', '' ) )
        field_0 = util.restore_text( kwd.get( 'field_0', '' ) )
        message = util.restore_text( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        url, http_method, request_params, response_type = request_tup
        url = unquote_plus( url )
        # Handle URLs in which we replace param values, which will look something like:
        # http://127.0.0.1/getinfo/{id}.
        replace_with_param = url.find( '{' ) > 0
        if replace_with_param:
            # Handle the special-case {JobId} param.
            if url.find( '{JobId}' ) > 0:
                if JobId:
                    url = url.replace( '{JobId}', str( JobId ) )
            for key, value in kwd.items():
                # Don't attempt to replace if there is nothing with which to do it
                # or if the value itself should be replaced with something.
                if value and not value.startswith( '{' ):
                    replace_str = '{%s}' % key
                    if url.find( replace_str ) > 0:
                        url = url.replace( replace_str, value )
        # Handle request parameters in which we replace param values.
        for key, val in request_params.items():
            if val and val.startswith( '{' ):
                replace_key = val.lstrip( '{' ).rstrip( '}' )
                if replace_key in kwd:
                    request_params[ key ] = kwd[ replace_key ]
        return url, http_method, request_params, response_type
    def handle_request( self, trans, url, http_method=None, **kwd ):
        if 'Name' in kwd and not kwd[ 'Name' ]:
            # Hack: specially handle parameters named "Name" if no param_value is given
            # by providing a date / time string - guarantees uniqueness, if required.
            kwd[ 'Name' ] = time.strftime( "%a, %d %b %Y %H:%M:%S", time.gmtime() )
        if 'Comments' in kwd and not kwd[ 'Comments' ]:
            # Hack: specially handle parameters named "Comments" if no param_value is given
            # by providing a date / time string.
            kwd[ 'Comments' ] = time.strftime( "%a, %d %b %Y %H:%M:%S", time.gmtime() )
        socket.setdefaulttimeout( 600 )
        # The following calls to urllib2.urlopen() will use the above default timeout.
        try:
            if not http_method or http_method == 'get':
                page = urllib2.urlopen( url )
                response = page.read()
                page.close()
                return response
            elif http_method == 'post':
                page = urllib2.urlopen( url, urllib.urlencode( kwd ) )
                response = page.read()
                page.close()
                return response
            elif http_method == 'put':
                url += '/' + str( kwd.pop( 'id' ) ) + '?key=' + kwd.pop( 'key' )
                output = self.put( url, **kwd )
        except Exception, e:
            raise
            message = 'Problem sending request to the web application: %s.  URL: %s.  kwd: %s.  Http method: %s' % \
            ( str( e ), str( url ), str( kwd ), str( http_method )  )
            return self.handle_failure( trans, url, message )
    def handle_failure( self, trans, url, message ):
        message = '%s, URL: %s' % ( message, url )
        params = dict( message = message,
                       status = 'error',
                       redirect_action = 'exit',
                       title = 'Error' )
        return trans.response.send_redirect( web.url_for( controller='common',
                                                          action='index',
                                                          **params ) )
    def put( self, url, **kwd ):
        opener = urllib2.build_opener( urllib2.HTTPHandler )
        request = urllib2.Request( url, data=to_json_string( kwd ) )
        request.add_header( 'Content-Type', 'application/json' )
        request.get_method = lambda: 'PUT'
        url = opener.open( request )
        output = url.read()
        return from_json_string( output )
