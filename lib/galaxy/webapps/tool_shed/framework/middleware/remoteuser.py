"""
Middleware for handling $REMOTE_USER if use_remote_user is enabled.
"""
import socket

from galaxy.util import safe_str_cmp

errorpage = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
    <head>
        <title>Galaxy</title>
        <style type="text/css">
        body {
            min-width: 500px;
            text-align: center;
        }
        .errormessage {
            font: 75%% verdana, "Bitstream Vera Sans", geneva, arial, helvetica, helve, sans-serif;
            padding: 10px;
            margin: 100px auto;
            min-height: 32px;
            max-width: 500px;
            border: 1px solid #AA6666;
            background-color: #FFCCCC;
            text-align: left;
        }
        </style>
    </head>
    <body>
        <div class="errormessage">
            <h4>%s</h4>
            <p>%s</p>
        </div>
    </body>
</html>
"""


class RemoteUser( object ):
    def __init__( self, app, maildomain=None, display_servers=None, admin_users=None, remote_user_secret_header=None ):
        self.app = app
        self.maildomain = maildomain
        self.display_servers = display_servers or []
        self.admin_users = admin_users or []
        self.config_secret_header = remote_user_secret_header

    def __call__( self, environ, start_response ):
        environ[ 'webapp' ] = 'tool_shed'
        # Allow display servers
        if self.display_servers and 'REMOTE_ADDR' in environ:
            try:
                host = socket.gethostbyaddr( environ[ 'REMOTE_ADDR' ] )[0]
            except( socket.error, socket.herror, socket.gaierror, socket.timeout ):
                # in the event of a lookup failure, deny access
                host = None
            if host in self.display_servers:
                environ[ 'HTTP_REMOTE_USER' ] = 'remote_display_server@%s' % ( self.maildomain or 'example.org' )
                return self.app( environ, start_response )

        # If the secret header is enabled, we expect upstream to send along some key
        # in HTTP_GX_SECRET, so we'll need to compare that here to the correct value
        #
        # This is not an ideal location for this function.  The reason being
        # that because this check is done BEFORE the REMOTE_USER check,  it is
        # possible to attack the GX_SECRET key without having correct
        # credentials. However, that's why it's not "ideal", but it is "good
        # enough". The only users able to exploit this are ones with access to
        # the local system (unless Galaxy is listening on 0.0.0.0....). It
        # seems improbable that an attacker with access to the server hosting
        # Galaxy would not have access to Galaxy itself, and be attempting to
        # attack the system
        if self.config_secret_header is not None:
            if not safe_str_cmp(environ.get('HTTP_GX_SECRET'), self.config_secret_header):
                title = "Access to Galaxy is denied"
                message = """
                Galaxy is configured to authenticate users via an external
                method (such as HTTP authentication in Apache), but an
                incorrect shared secret key was provided by the
                upstream (proxy) server.</p>
                <p>Please contact your local Galaxy administrator.  The
                variable <code>remote_user_secret</code> and
                <code>GX_SECRET</code> header must be set before you may
                access Galaxy.
                """
                return self.error( start_response, title, message )

        # Apache sets REMOTE_USER to the string '(null)' when using the Rewrite* method for passing REMOTE_USER and a user is
        # un-authenticated.  Any other possible values need to go here as well.
        path_info = environ.get('PATH_INFO', '')
        if 'HTTP_REMOTE_USER' in environ and environ[ 'HTTP_REMOTE_USER' ] != '(null)':
            if not environ[ 'HTTP_REMOTE_USER' ].count( '@' ):
                if self.maildomain is not None:
                    environ[ 'HTTP_REMOTE_USER' ] += '@' + self.maildomain
                else:
                    title = "Access to this Galaxy tool shed is denied"
                    message = """
                        This Galaxy tool shed is configured to authenticate users via an external
                        method (such as HTTP authentication in Apache), but only a username (not
                        an email address) was provided by the upstream (proxy) server.  Since tool
                        shed usernames are email addresses, a default mail domain must be set.</[>
                        <p>The variable <code>remote_user_maildomain</code> must be set before you
                        can access this tool shed.  Contact your local tool shed administrator.
                    """
                    return self.error( start_response, title, message )
            return self.app( environ, start_response )
        elif path_info.startswith( '/api/' ):
            # The API handles its own authentication via keys
            return self.app( environ, start_response )
        elif path_info.startswith( '/user/api_keys' ):
            # api_keys can be managed when remote_user is in use.
            pass
        else:
            title = "Access to this Galaxy tool shed is denied"
            message = """
                This Galaxy tool shed is configured to authenticate users via an external
                method (such as HTTP authentication in Apache), but a username was not
                provided by the upstream (proxy) server.  This is generally due to a
                misconfiguration in the upstream server.</p>
                <p>Contact your local Galaxy tool shed administrator.
            """
            return self.error( start_response, title, message )

    def error( self, start_response, title="Access denied", message="Contact your local Galaxy tool shed administrator." ):
        start_response( '403 Forbidden', [('Content-type', 'text/html')] )
        return [errorpage % (title, message)]
