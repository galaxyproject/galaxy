from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago
from galaxy import util
import time, socket, urllib, urllib2, base64
from galaxy.util.json import *

import logging
log = logging.getLogger( __name__ )

class CommonController( BaseController ):
    @web.expose
    def index( self, trans, **kwd ):
        log.debug("#####In index, kwd: %s" % str( kwd ))
        params = util.Params( kwd )
        redirect_action = util.restore_text( params.get( 'redirect_action', '' ) )
        title = util.restore_text( params.get( 'title', '' ) )
        JobId = util.restore_text( params.get( 'JobId', '' ) )
        message = util.restore_text( params.get( 'message', '' ) )
        status = params.get( 'status', 'done' )
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
                url, http_method, request_params, response_type = self.parse_request_tup( request_tup, JobId )
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
                        # Move to the next action, if there is one
                        redirect_action = sequencer_redirects.keys()[ index + 1 ]
                        action_dict = sequencer_redirects[ redirect_action ]
                        title = action_dict[ 'title' ]
                    except:
                        # Keep displaying the same title on the page until we redirect ( if we do )
                        action_dict = sequencer_redirects[ redirect_action ]
                        title = action_dict[ 'title' ]
                        # If we're done redirecting, stop
                        redirect_action = 'stop'
                    break
        # Handle requests, if there are any
        for request_tup in requests:
            url, http_method, request_params, response_type = self.parse_request_tup( request_tup, JobId )
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
                    JobId = response[ 'JobId' ]
        time.sleep( redirect_delay )
        return trans.fill_template( "webapps/demo_sequencer/index.mako",
                                    redirect_action=redirect_action,
                                    title=title,
                                    JobId=JobId,
                                    message=message,
                                    status=status )
    def parse_request_tup( self, request_tup, JobId ):
        url, http_method, request_params, response_type = request_tup
        # Some requests can look like this: http://127.0.0.1/getinfo/{id}
        # which requires us to replace the {id} string with a param value
        # in the XML config that has the same name.  This is a hack,
        # especially since it only handles a single replacement, but works
        # for now...
        replace_with_param = url.find( '{' ) > 0
        if replace_with_param:
            # Get the location of the item that needs to be replaced so we can
            # rebuild the request with the proper value/
            split_url = url.split( '/' )
            for index, item in enumerate( split_url ):
                if item.startswith( '{' ):
                    item = item.lstrip( '{' )
                    item = item.rstrip( '}' )
                    if item == 'JobId':
                        if JobId:
                            # JobId is a special parameter since it is unknown until the job is created,
                            # so we need this hack.
                            item = JobId
                            split_url[ index ] = str( item )
                    else:
                        # Get the value from the defined request_params dict
                        item = request_params[ item ]
                        del request_params[ item ]
                        split_url[ index ] = str( item )
                    break
            url = '/'.join( split_url )
        return url, http_method, request_params, response_type
    def handle_request( self, trans, url, http_method=None, **kwd ):
        # The Python support for fetching resources from the web is layered. urllib2 uses the httplib
        # library, which in turn uses the socket library.  As of Python 2.3 you can specify how long
        # a socket should wait for a response before timing out. By default the socket module has no
        # timeout and can hang. Currently, the socket timeout is not exposed at the httplib or urllib2
        # levels. However, you can set the default timeout ( in seconds ) globally for all sockets by
        # doing the following.
        socket.setdefaulttimeout( 600 )
        # The following calls to urllib2.urlopen() will use the above default timeout
        try:
            if not http_method or http_method == 'get':
                page = urllib2.urlopen( url )
            elif http_method == 'post':
                page = urllib2.urlopen( url, urllib.urlencode( kwd ) )
            response = page.read()
            page.close()
            return response
        except Exception, e:
            message = 'Problem sending request to the web application. Error: %s' % str( e )
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
