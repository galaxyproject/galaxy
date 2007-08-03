"""
Provides factory methods to assemble the Galaxy web application
"""

import logging, atexit

from paste.request import parse_formvars
from paste.util import import_string
from paste import httpexceptions
from paste.deploy.converters import asbool
import flup.middleware.session as flup_session
import pkg_resources

log = logging.getLogger( __name__ )

from galaxy import config, jobs, util, tools
import galaxy.model
import galaxy.model.mapping
import galaxy.datatypes.registry
from galaxy.web.controllers import root, tool_runner, proxy, async, admin, user, error, dataset

import galaxy.web.framework

def app_factory( global_conf, **kwargs ):
    """
    Return a wsgi application serving the root object
    """
    # Create the Galaxy application unless passed in
    if 'app' in kwargs:
        app = kwargs.pop( 'app' )
    else:
        from galaxy.app import UniverseApplication
        app = UniverseApplication( global_conf = global_conf, **kwargs )
    atexit.register( app.shutdown )
    # Create the universe WSGI application
    webapp = galaxy.web.framework.WebApplication( app )
    # Add controllers to the web application
    webapp.add_controller( 'root', root.Universe( app ) )
    webapp.add_controller( 'tool_runner', tool_runner.ToolRunner( app ) )
    webapp.add_controller( 'ucsc_proxy', proxy.UCSCProxy( app ) )
    webapp.add_controller( 'async', async.ASync( app ) )
    webapp.add_controller( 'admin', admin.Admin( app ) )
    webapp.add_controller( 'user', user.User( app ) )
    webapp.add_controller( 'error', error.Error( app ) )
    webapp.add_controller( 'dataset', dataset.DatasetInterface( app ) )
    # These two routes handle our simple needs at the moment
    webapp.add_route( '/async/:tool_id/:data_id/:data_secret', controller='async', action='index', tool_id=None, data_id=None, data_secret=None )
    webapp.add_route( '/:controller/:action', action='index' )
    webapp.add_route( '/:action', controller='root', action='index' )
    webapp.finalize_config()
    # Wrap the webapp in some useful middleware
    if kwargs.get( 'middleware', True ):
        webapp = wrap_in_middleware( webapp, global_conf, **kwargs )
    if kwargs.get( 'static_enabled', True ):
        webapp = wrap_in_static( webapp, global_conf, **kwargs )
    # Close any pooled database connections before forking
    try:
        galaxy.model.mapping.metadata.engine.connection_provider._pool.dispose()
    except:
        pass
    # Return
    return webapp
    
def wrap_in_middleware( app, global_conf, **local_conf ):
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
    ## # Session middleware puts a session factory into the environment 
    ## if asbool( conf.get( 'use_session', True ) ):
    ##     store = flup_session.MemorySessionStore()
    ##     app = flup_session.SessionMiddleware( store, app )
    ##     log.debug( "Enabling 'flup session' middleware" )
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
    from galaxy.web.framework.middleware.xforwardedhost import XForwardedHostMiddleware
    app = XForwardedHostMiddleware( app )
    log.debug( "Enabling 'x-forwarded-host' middleware" )
    return app
    
def wrap_in_static( app, global_conf, **local_conf ):
    from paste.urlmap import URLMap
    from galaxy.web.framework.middleware.static import CacheableStaticURLParser as Static
    urlmap = URLMap()
    # Merge the global and local configurations
    conf = global_conf.copy()
    conf.update(local_conf)
    # Get cache time in seconds
    cache_time = conf.get( "static_cache_time", None )
    if cache_time is not None:
        cache_time = int( cache_time )
    # Send to dynamic app by default
    urlmap["/"] = app
    # Define static mappings from config
    urlmap["/static"] = Static( conf.get( "static_dir" ), cache_time )
    urlmap["/images"] = Static( conf.get( "static_images_dir" ), cache_time )
    urlmap["/static/scripts"] = Static( conf.get( "static_scripts_dir" ), cache_time )
    urlmap["/static/style"] = Static( conf.get( "static_style_dir" ), cache_time )
    urlmap["/favicon.ico"] = Static( conf.get( "static_favicon_dir" ), cache_time )
    # URL mapper becomes the root webapp
    return urlmap
    
    
