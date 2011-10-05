from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago
from galaxy import util
import time, socket, urllib, urllib2, base64, copy
from galaxy.util.json import *
from urllib import quote_plus, unquote_plus

import logging
log = logging.getLogger( __name__ )

class CommonController( BaseUIController ):
    @web.expose
    def index( self, trans, **kwd ):
        redirect_action = util.restore_text( kwd.get( 'redirect_action', '' ) )
        titles = util.restore_text( kwd.get( 'titles', '' ) )
        titles = util.listify( titles )
        JobId = util.restore_text( kwd.get( 'JobId', '' ) )
        sample_id = util.restore_text( kwd.get( 'sample_id', '' ) )
        message = util.restore_text( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        redirect_delay = trans.app.sequencer_actions_registry.redirect_delay
        sequencer_redirects = copy.deepcopy( trans.app.sequencer_actions_registry.sequencer_redirects )
        sequencer_requests = copy.deepcopy( trans.app.sequencer_actions_registry.sequencer_requests )
        requests = []
        if redirect_action == 'stop':
            # Handle any additional requests
            for request_tup in sequencer_requests:
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
            # Handle the final redirect, if any ( should only be 0 or 1 ).
            for request_tup in trans.app.sequencer_actions_registry.final_redirect:
                url, http_method, request_params, response_type = self.parse_request_tup( request_tup, **kwd )
                return trans.fill_template( 'webapps/demo_sequencer/redirect.mako', redirect_url=url )
            # Exit if we have no redirection
            redirect_action = 'exit'
        elif not redirect_action:
            # Specially handle the initial request to the demo sequencer by starting with the first defined redirect.
            redirect_action, action_dict = sequencer_redirects.items()[0]
            titles = [ action_dict[ 'title' ] ]
            if 'requests' in action_dict:
                requests = action_dict[ 'requests' ]
        else:
            for index, key in enumerate( sequencer_redirects.iterkeys() ):
                if redirect_action == key:
                    try:
                        # Move to the next action, if there is one.
                        redirect_action = sequencer_redirects.keys()[ index + 1 ]
                        action_dict = sequencer_redirects[ redirect_action ]
                        titles.append( action_dict[ 'title' ] )
                    except:
                        # If we're done redirecting, stop.
                        redirect_action = 'stop'
                    break
        if not trans.app.sequencer_actions_registry.authenticated:
            # Support various types of authentication
            if trans.app.sequencer_actions_registry.browser_login:
                # We'll just build the URL here since authentication will be handled in the browser
                url = trans.app.sequencer_actions_registry.browser_login[ 'url' ]
                params = trans.app.sequencer_actions_registry.browser_login[ 'params' ]
                trans.app.sequencer_actions_registry.browser_login = '%s?%s' %( url, urllib.urlencode( params ) )
                if not trans.app.sequencer_actions_registry.final_redirect:
                    # If we don't have a final_redirect tag, but we want our browser to authenticate,
                    # do it ow.  If we have a final_redirect tag, browser authentication will happen there.
                    url = web.url_for( controller='common', action='index', **kwd )
                    return trans.fill_template( 'webapps/demo_sequencer/redirect.mako', redirect_url=url )
            if trans.app.sequencer_actions_registry.basic_http_authentication:
                # Example tag:
                # <basic_http_authentication user="administrator" password="galaxy" url="http://127.0.0.1" realm="" />
                user, password, url, realm = trans.app.sequencer_actions_registry.basic_http_authentication
                # Create a password manager
                password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
                # Add the username, password and realm.
                if not realm:
                    realm = None
                password_mgr.add_password( realm, url, user, password )
                handler = urllib2.HTTPBasicAuthHandler( password_mgr )
                # Create "opener" (OpenerDirector instance)
                opener = urllib2.build_opener( handler )
                # Install the opener, now all calls to urllib2.urlopen use our opener.
                urllib2.install_opener( opener )
                trans.app.sequencer_actions_registry.authenticated = True
            if trans.app.sequencer_actions_registry.http_headers_authorization:
                # Example tag:
                # <http_headers_authorization credentials="administrator:galaxy" url="http://127.0.0.1" />
                url, credentials = trans.app.sequencer_actions_registry.http_headers_authorization
                req = urllib2.Request( url )
                req.add_header( 'Authorization', 'Basic %s' % base64.b64encode( credentials ) )
                trans.app.sequencer_actions_registry.authenticated = True
            if trans.app.sequencer_actions_registry.http_cookie_processor_authentication:
                # Example tag:
                # <http_cookie_processor_authentication url="http://127.0.0.1/login">
                #    <param name="user" value="administrator"/>
                #    <param name="password" value="galaxy"/>
                # </http_cookie_processor_authentication>
                url = trans.app.sequencer_actions_registry.http_cookie_processor_authentication[ 'url' ]
                params = trans.app.sequencer_actions_registry.http_cookie_processor_authentication[ 'params' ]
                # Build opener with HTTPCookieProcessor
                opener = urllib2.build_opener( urllib2.HTTPCookieProcessor() )
                urllib2.install_opener( opener )
                # Perform login with params
                page = opener.open( url, urllib.urlencode( params ) )
                response = page.read()
                page.close()
                # Any additional requests should automatically pass back any
                # cookies received during login, thanks to the HTTPCookieProcessor
                trans.app.sequencer_actions_registry.authenticated = True
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
        titles = ','.join( titles )
        return trans.fill_template( "webapps/demo_sequencer/index.mako",
                                    redirect_action=redirect_action,
                                    redirect_delay=redirect_delay,
                                    titles=titles,
                                    sample_id=sample_id,
                                    JobId=JobId,
                                    message=message,
                                    status=status )
    def parse_request_tup( self, request_tup, **kwd ):
        redirect_action = util.restore_text( kwd.get( 'redirect_action', '' ) )
        titles = util.restore_text( kwd.get( 'titles', '' ) )
        JobId = util.restore_text( kwd.get( 'JobId', '' ) )
        sample_id = util.restore_text( kwd.get( 'sample_id', '' ) )
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
                       titles = 'Error' )
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
    @web.expose
    def login( self, trans, **kwd ):
        trans.app.sequencer_actions_registry.authenticated = True
        return trans.fill_template( "webapps/demo_sequencer/login.mako" )
    @web.expose
    def empty_page( self, trans, **kwd ):
        # Hack to not display responses in the browser - src for a hidden iframe.
        return trans.fill_template( "webapps/demo_sequencer/empty.mako" )
