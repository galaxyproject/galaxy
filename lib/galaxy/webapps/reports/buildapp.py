"""
Provides factory methods to assemble the Galaxy web application
"""

import logging
import atexit
import os

from inspect import isclass

from paste import httpexceptions

from galaxy.util import asbool
from galaxy.util.postfork import process_is_uwsgi
from galaxy.webapps.util import build_template_error_formatters

import galaxy.model
import galaxy.model.mapping
import galaxy.web.framework.webapp
from galaxy.util.properties import load_app_properties

log = logging.getLogger( __name__ )


class ReportsWebApplication( galaxy.web.framework.webapp.WebApplication ):
    pass


def add_ui_controllers( webapp, app ):
    """
    Search for controllers in the 'galaxy.webapps.controllers' module and add
    them to the webapp.
    """
    from galaxy.web.base.controller import BaseUIController
    import galaxy.webapps.reports.controllers
    controller_dir = galaxy.webapps.reports.controllers.__path__[0]
    for fname in os.listdir( controller_dir ):
        if not fname.startswith( "_" ) and fname.endswith( ".py" ):
            name = fname[:-3]
            module_name = "galaxy.webapps.reports.controllers." + name
            module = __import__( module_name )
            for comp in module_name.split( "." )[1:]:
                module = getattr( module, comp )
            # Look for a controller inside the modules
            for key in dir( module ):
                T = getattr( module, key )
                if isclass( T ) and T is not BaseUIController and issubclass( T, BaseUIController ):
                    webapp.add_ui_controller( name, T( app ) )


def app_factory( global_conf, **kwargs ):
    """Return a wsgi application serving the root object"""
    # Create the Galaxy application unless passed in
    kwargs = load_app_properties(
        kwds=kwargs
    )
    if 'app' in kwargs:
        app = kwargs.pop( 'app' )
    else:
        from galaxy.webapps.reports.app import UniverseApplication
        app = UniverseApplication( global_conf=global_conf, **kwargs )
    atexit.register( app.shutdown )
    # Create the universe WSGI application
    webapp = ReportsWebApplication( app, session_cookie='galaxyreportssession', name="reports" )
    add_ui_controllers( webapp, app )
    # These two routes handle our simple needs at the moment
    webapp.add_route( '/{controller}/{action}', controller="root", action='index' )
    webapp.add_route( '/{action}', controller='root', action='index' )
    webapp.finalize_config()
    # Wrap the webapp in some useful middleware
    if kwargs.get( 'middleware', True ):
        webapp = wrap_in_middleware( webapp, global_conf, **kwargs )
    if asbool( kwargs.get( 'static_enabled', True ) ):
        webapp = wrap_in_static( webapp, global_conf, **kwargs )
    # Close any pooled database connections before forking
    try:
        galaxy.model.mapping.metadata.bind.dispose()
    except:
        log.exception("Unable to dispose of pooled galaxy model database connections.")
    # Return
    return webapp


def wrap_in_middleware( app, global_conf, **local_conf ):
    """Based on the configuration wrap `app` in a set of common and useful middleware."""
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
        # Middleware that intercepts print statements and shows them on the
        # returned page
        if asbool( conf.get( 'use_printdebug', True ) ):
            from paste.debug import prints
            app = prints.PrintDebugMiddleware( app, conf )
            log.debug( "Enabling 'print debug' middleware" )
    if debug and asbool( conf.get( 'use_interactive', False ) ) and not process_is_uwsgi:
        # Interactive exception debugging, scary dangerous if publicly
        # accessible, if not enabled we'll use the regular error printing
        # middleware.
        from weberror import evalexception
        app = evalexception.EvalException( app, conf,
                                           templating_formatters=build_template_error_formatters() )
        log.debug( "Enabling 'eval exceptions' middleware" )
    else:
        if debug and asbool( conf.get( 'use_interactive', False ) ) and process_is_uwsgi:
            log.error("Interactive debugging middleware is enabled in your configuration "
                      "but this is a uwsgi process.  Refusing to wrap in interactive error middleware.")
        # Not in interactive debug mode, just use the regular error middleware
        from paste.exceptions import errormiddleware
        app = errormiddleware.ErrorMiddleware( app, conf )
        log.debug( "Enabling 'error' middleware" )
    # Transaction logging (apache access.log style)
    if asbool( conf.get( 'use_translogger', True ) ):
        from paste.translogger import TransLogger
        app = TransLogger( app )
        log.debug( "Enabling 'trans logger' middleware" )
    # X-Forwarded-Host handling
    from galaxy.web.framework.middleware.xforwardedhost import XForwardedHostMiddleware
    app = XForwardedHostMiddleware( app )
    log.debug( "Enabling 'x-forwarded-host' middleware" )
    return app


def wrap_in_static( app, global_conf, **local_conf ):
    urlmap, _ = galaxy.web.framework.webapp.build_url_map( app, global_conf, local_conf )
    return urlmap
