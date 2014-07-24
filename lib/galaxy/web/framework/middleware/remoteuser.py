"""
Middleware for handling $REMOTE_USER if use_remote_user is enabled.
"""

import socket

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
    def __init__( self, app, maildomain=None, display_servers=None, admin_users=None, remote_user_header=None ):
        self.app = app
        self.maildomain = maildomain
        self.display_servers = display_servers or []
        self.admin_users = admin_users or []
        self.remote_user_header = remote_user_header or 'HTTP_REMOTE_USER'

    def __call__( self, environ, start_response ):
        # Allow display servers
        if self.display_servers and 'REMOTE_ADDR' in environ:
            try:
                host = socket.gethostbyaddr( environ[ 'REMOTE_ADDR' ] )[0]
            except( socket.error, socket.herror, socket.gaierror, socket.timeout ):
                # in the event of a lookup failure, deny access
                host = None
            if host in self.display_servers:
                environ[ self.remote_user_header ] = 'remote_display_server@%s' % ( self.maildomain or 'example.org' )
                return self.app( environ, start_response )
        # Apache sets REMOTE_USER to the string '(null)' when using the
        # Rewrite* method for passing REMOTE_USER and a user is
        # un-authenticated.  Any other possible values need to go here as well.
        path_info = environ.get('PATH_INFO', '')
        if environ.get(self.remote_user_header, '(null)') != '(null)':
            if not environ[ self.remote_user_header ].count( '@' ):
                if self.maildomain is not None:
                    environ[ self.remote_user_header ] += '@' + self.maildomain
                else:
                    title = "Access to Galaxy is denied"
                    message = """
                        Galaxy is configured to authenticate users via an external
                        method (such as HTTP authentication in Apache), but only a
                        username (not an email address) was provided by the
                        upstream (proxy) server.  Since Galaxy usernames are email
                        addresses, a default mail domain must be set.</p>
                        <p>Please contact your local Galaxy administrator.  The
                        variable <code>remote_user_maildomain</code> must be set
                        before you may access Galaxy.
                    """
                    return self.error( start_response, title, message )
            if not path_info.startswith('/user'):
                # shortcut the following whitelist for non-user-controller
                # requests.
                pass
            elif path_info.startswith( '/user/create' ) and environ[ self.remote_user_header ] in self.admin_users:
                pass  # admins can create users
            elif path_info.startswith( '/user/logout' ) and environ[ self.remote_user_header ] in self.admin_users:
                pass  # Admin users may be impersonating, allow logout.
            elif path_info.startswith( '/user/api_keys' ):
                pass  # api keys can be managed when remote_user is in use
            elif path_info.startswith( '/user/edit_username' ):
                pass  # username can be managed when remote_user is in use
            elif path_info.startswith( '/user/dbkeys' ):
                pass  # dbkeys can be managed when remote_user is in use
            elif path_info.startswith( '/user/toolbox_filters' ):
                pass  # toolbox filters can be managed when remote_user is in use
            elif path_info.startswith( '/user/set_default_permissions' ):
                pass  # default permissions can be managed when remote_user is in use
            elif path_info == '/user' or path_info == '/user/':
                pass  # We do allow access to the root user preferences page.
            elif path_info.startswith( '/user' ):
                # Any other endpoint in the user controller is off limits
                title = "Access to Galaxy user controls is disabled"
                message = """
                    User controls are disabled when Galaxy is configured
                    for external authentication.
                """
                return self.error( start_response, title, message )
            return self.app( environ, start_response )
        elif path_info.startswith( '/api/' ):
            # The API handles its own authentication via keys
            return self.app( environ, start_response )
        else:
            title = "Access to Galaxy is denied"
            message = """
                Galaxy is configured to authenticate users via an external
                method (such as HTTP authentication in Apache), but a username
                was not provided by the upstream (proxy) server.  This is
                generally due to a misconfiguration in the upstream server.</p>
                <p>Please contact your local Galaxy administrator.
            """
            return self.error( start_response, title, message )

    def error( self, start_response, title="Access denied", message="Please contact your local Galaxy administrator." ):
        start_response( '403 Forbidden', [('Content-type', 'text/html')] )
        return [errorpage % (title, message)]
