"""
Middleware for handling $REMOTE_USER if use_remote_user is enabled.
"""

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
    def __init__( self, app, maildomain=None ):
        self.app = app
        self.maildomain = maildomain
    def __call__( self, environ, start_response ):
        # Apache sets REMOTE_USER to the string '(null)' when using the
        # Rewrite* method for passing REMOTE_USER and a user is
        # un-authenticated.  Any other possible values need to go here as well.
        if environ.has_key( 'HTTP_REMOTE_USER' ) and environ[ 'HTTP_REMOTE_USER' ] != '(null)':
            path_info = environ.get('PATH_INFO', '')
            if path_info.startswith( '/user' ):
                title = "Access to Galaxy user controls is disabled"
                message = """
                    User controls are disabled when Galaxy is configured
                    for external authentication.
                """
                return self.error( start_response, title, message )
            elif not environ[ 'HTTP_REMOTE_USER' ].count( '@' ):
                if self.maildomain is not None:
                    environ[ 'HTTP_REMOTE_USER' ] += '@' + self.maildomain
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
