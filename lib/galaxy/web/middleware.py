import logging

from paste.request import parse_formvars
from paste.util import import_string
from paste import httpexceptions
from paste.deploy.converters import asbool
import flup.middleware.session as flup_session
import pkg_resources

log = logging.getLogger( __name__ )

class XForwardedHostMiddleware( object ):
    """
    A WSGI middleware that changes the HTTP host header in the WSGI environ
    based on the X-Forwarded-Host header IF found 
    """
    def __init__( self, app, global_conf=None ):
        self.app = app
    def __call__( self, environ, start_response ):
        x_forwarded_host = environ.get( 'HTTP_X_FORWARDED_HOST', None )
        if x_forwarded_host:
            environ[ 'ORGINAL_HTTP_HOST' ] = environ[ 'HTTP_HOST' ]
            environ[ 'HTTP_HOST' ] = x_forwarded_host
        x_forwarded_for = environ.get( 'HTTP_X_FORWARDED_FOR', None )
        if x_forwarded_for:
            environ[ 'ORGINAL_REMOTE_ADDR' ] = environ[ 'REMOTE_ADDR' ]
            environ[ 'REMOTE_ADDR' ] = x_forwarded_for
        return self.app( environ, start_response )

def make_middleware( app, global_conf, **local_conf ):
    """
    Based on the configuration wrap `app` in a set of common and useful 
    middleware.
    """
    # Merge the global and local configurations
    conf = global_conf.copy()
    conf.update(local_conf)
    debug = asbool( conf.get( 'debug', False ) )
    # First put into place httpexceptions, which must be most closely
    # wrapped around the application (it can interact poorly with
    # other middleware):
    app = httpexceptions.make_middleware( app, conf )
    log.debug( "Enabling 'httpexceptions' middleware" )
    # The recursive middleware allows for including requests in other 
    # requests or forwarding of requests, all on the server side.
    if asbool(conf.get('use_recursive', True)):
        from paste import recursive
        app = recursive.RecursiveMiddleware( app, conf )
        log.debug( "Enabling 'recursive' middleware" )
    # Session middleware puts a session factory into the environment 
    if asbool( conf.get( 'use_session', True ) ):
        store = flup_session.MemorySessionStore()
        app = flup_session.SessionMiddleware( store, app )
        log.debug( "Enabling 'flup session' middleware" )
    # Beaker session middleware
    if asbool( conf.get( 'use_beaker_session', False ) ):
        pkg_resources.require( "Beaker" )
        import beaker.session
        app = beaker.session.SessionMiddleware( app, conf )
        log.debug( "Enabling 'beaker session' middleware" )
    # Various debug middleware that can only be turned on if the debug
    # flag is set, either because they are insecure or greatly hurt
    # performance
    if debug:
        # Middleware to check for WSGI compliance
        if asbool( conf.get( 'use_lint', True ) ):
            from paste import lint
            app = lint.make_middleware( app, conf )
            log.debug( "Enabling 'lint' middleware" )
        # Middleware to run the python profiler on each request
        if asbool( conf.get( 'use_profile', False ) ):
            import profile
            app = profile.ProfileMiddleware( app, conf )
            log.debug( "Enabling 'profile' middleware" )
        # Interactive exception debugging, scary dangerous if publicly
        # accessible, if not enabled we'll use the regular error printing
        # middleware.
        if asbool( conf.get( 'use_interactive', False ) ):
            from paste import evalexception
            app = evalexception.EvalException( app, conf )
            log.debug( "Enabling 'eval exceptions' middleware" )
        else:
            from paste.exceptions import errormiddleware
            app = errormiddleware.ErrorMiddleware( app, conf )
            log.debug( "Enabling 'error' middleware" )
        # Middleware that intercepts print statements and shows them on the
        # returned page
        if asbool( conf.get( 'use_printdebug', True ) ):
            from paste.debug import prints
            app = prints.PrintDebugMiddleware( app, conf )
            log.debug( "Enabling 'print debug' middleware" )
    else:
        # Not in debug mode, just use the regular error middleware
        from paste.exceptions import errormiddleware
        app = errormiddleware.ErrorMiddleware( app, conf )
        log.debug( "Enabling 'error' middleware" )
    # Transaction logging (apache access.log style)
    if asbool( conf.get( 'use_translogger', True ) ):
        from paste.translogger import TransLogger
        app = TransLogger( app )
        log.debug( "Enabling 'trans logger' middleware" )
    # Config middleware just stores the paste config along with the request,
    # not sure we need this but useful
    from paste.deploy.config import ConfigMiddleware
    app = ConfigMiddleware( app, conf )
    log.debug( "Enabling 'config' middleware" )
    # X-Forwarded-Host handling
    app = XForwardedHostMiddleware( app )
    log.debug( "Enabling 'x-forwarded-host' middleware" )
    return app
