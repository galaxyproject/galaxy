"""
Provides factory methods to assemble the Galaxy web application
"""

import logging, atexit
import os, os.path
import sys, warnings

from inspect import isclass

from paste.request import parse_formvars
from paste.util import import_string
from paste import httpexceptions
from paste.deploy.converters import asbool
import pkg_resources

log = logging.getLogger( __name__ )

from galaxy import config, jobs, util, tools
import galaxy.model
import galaxy.model.mapping
import galaxy.datatypes.registry
import galaxy.web.framework

def add_ui_controllers( webapp, app ):
    """
    Search for controllers in the 'galaxy.web.controllers' module and add 
    them to the webapp.
    """
    from galaxy.web.base.controller import BaseUIController
    from galaxy.web.base.controller import ControllerUnavailable
    import galaxy.web.controllers
    controller_dir = galaxy.web.controllers.__path__[0]
    for fname in os.listdir( controller_dir ):
        if not( fname.startswith( "_" ) ) and fname.endswith( ".py" ):
            name = fname[:-3]
            module_name = "galaxy.web.controllers." + name
            try:
                module = __import__( module_name )
            except ControllerUnavailable, exc:
                log.debug("%s could not be loaded: %s" % (module_name, str(exc)))
                continue
            for comp in module_name.split( "." )[1:]:
                module = getattr( module, comp )
            # Look for a controller inside the modules
            for key in dir( module ):
                T = getattr( module, key )
                if isclass( T ) and T is not BaseUIController and issubclass( T, BaseUIController ):
                    webapp.add_ui_controller( name, T( app ) )

def add_api_controllers( webapp, app ):
    from galaxy.web.base.controller import BaseAPIController
    from galaxy.web.base.controller import ControllerUnavailable
    import galaxy.web.api
    controller_dir = galaxy.web.api.__path__[0]
    for fname in os.listdir( controller_dir ):
        if not( fname.startswith( "_" ) ) and fname.endswith( ".py" ):
            name = fname[:-3]
            module_name = "galaxy.web.api." + name
            try:
                module = __import__( module_name )
            except ControllerUnavailable, exc:
                log.debug("%s could not be loaded: %s" % (module_name, str(exc)))
                continue
            for comp in module_name.split( "." )[1:]:
                module = getattr( module, comp )
            for key in dir( module ):
                T = getattr( module, key )
                if isclass( T ) and T is not BaseAPIController and issubclass( T, BaseAPIController ):
                    webapp.add_api_controller( name, T( app ) )

def app_factory( global_conf, **kwargs ):
    """
    Return a wsgi application serving the root object
    """
    # Create the Galaxy application unless passed in
    if 'app' in kwargs:
        app = kwargs.pop( 'app' )
    else:
        try:
            from galaxy.app import UniverseApplication
            app = UniverseApplication( global_conf = global_conf, **kwargs )
        except:
            import traceback, sys
            traceback.print_exc()
            sys.exit( 1 )
    atexit.register( app.shutdown )
    # Create the universe WSGI application
    webapp = galaxy.web.framework.WebApplication( app, session_cookie='galaxysession' )
    add_ui_controllers( webapp, app )
    # Force /history to go to /root/history -- needed since the tests assume this
    webapp.add_route( '/history', controller='root', action='history' )
    # These two routes handle our simple needs at the moment
    webapp.add_route( '/async/:tool_id/:data_id/:data_secret', controller='async', action='index', tool_id=None, data_id=None, data_secret=None )
    webapp.add_route( '/:controller/:action', action='index' )
    webapp.add_route( '/:action', controller='root', action='index' )
    # allow for subdirectories in extra_files_path
    webapp.add_route( '/datasets/:dataset_id/display/{filename:.+?}', controller='dataset', action='display', dataset_id=None, filename=None)
    webapp.add_route( '/datasets/:dataset_id/:action/:filename', controller='dataset', action='index', dataset_id=None, filename=None)
    webapp.add_route( '/display_application/:dataset_id/:app_name/:link_name/:user_id/:app_action/:action_param', controller='dataset', action='display_application', dataset_id=None, user_id=None, app_name = None, link_name = None, app_action = None, action_param = None )
    webapp.add_route( '/u/:username/d/:slug/:filename', controller='dataset', action='display_by_username_and_slug', filename=None )
    webapp.add_route( '/u/:username/p/:slug', controller='page', action='display_by_username_and_slug' )
    webapp.add_route( '/u/:username/h/:slug', controller='history', action='display_by_username_and_slug' )
    webapp.add_route( '/u/:username/w/:slug', controller='workflow', action='display_by_username_and_slug' )
    webapp.add_route( '/u/:username/v/:slug', controller='visualization', action='display_by_username_and_slug' )
    
    # Add the web API
    add_api_controllers( webapp, app )
    webapp.api_mapper.resource( 'content',
                                'contents',
                                controller='library_contents',
                                name_prefix='library_',
                                path_prefix='/api/libraries/:library_id', 
                                parent_resources=dict( member_name='library', collection_name='libraries' ) )
    webapp.api_mapper.resource( 'content',
                                'contents',
                                controller='history_contents',
                                name_prefix='history_',
                                path_prefix='/api/histories/:history_id', 
                                parent_resources=dict( member_name='history', collection_name='histories' ) )
    webapp.api_mapper.resource( 'permission',
                                'permissions',
                                path_prefix='/api/libraries/:library_id',
                                parent_resources=dict( member_name='library', collection_name='libraries' ) )      
    webapp.api_mapper.resource( 'dataset', 'datasets', path_prefix='/api' )
    webapp.api_mapper.resource_with_deleted( 'library', 'libraries', path_prefix='/api' )
    webapp.api_mapper.resource( 'sample', 'samples', path_prefix='/api' )
    webapp.api_mapper.resource( 'request', 'requests', path_prefix='/api' )
    webapp.api_mapper.resource( 'form', 'forms', path_prefix='/api' )
    webapp.api_mapper.resource( 'request_type', 'request_types', path_prefix='/api' )
    webapp.api_mapper.resource( 'role', 'roles', path_prefix='/api' )
    webapp.api_mapper.resource_with_deleted( 'quota', 'quotas', path_prefix='/api' )
    webapp.api_mapper.resource( 'tool', 'tools', path_prefix='/api' )
    webapp.api_mapper.resource_with_deleted( 'user', 'users', path_prefix='/api' )
    webapp.api_mapper.resource( 'workflow', 'workflows', path_prefix='/api' )
    webapp.api_mapper.resource_with_deleted( 'history', 'histories', path_prefix='/api' )
    #webapp.api_mapper.connect( 'run_workflow', '/api/workflow/{workflow_id}/library/{library_id}', controller='workflows', action='run', workflow_id=None, library_id=None, conditions=dict(method=["GET"]) )

    webapp.finalize_config()
    # Wrap the webapp in some useful middleware
    if kwargs.get( 'middleware', True ):
        webapp = wrap_in_middleware( webapp, global_conf, **kwargs )
    if asbool( kwargs.get( 'static_enabled', True ) ):
        webapp = wrap_in_static( webapp, global_conf, **kwargs )
    if asbool(kwargs.get('pack_scripts', False)):
        pack_scripts()
    # Close any pooled database connections before forking
    try:
        galaxy.model.mapping.metadata.engine.connection_provider._pool.dispose()
    except:
        pass
    # Return
    return webapp

def pack_scripts():
    from glob import glob
    from subprocess import call
    cmd = "java -jar scripts/yuicompressor.jar --type js static/scripts/%(fname)s -o static/scripts/packed/%(fname)s"
    raw_js= [os.path.basename(g) for g in glob( "static/scripts/*.js" )]
    for fname in raw_js:
        if os.path.exists('static/scripts/packed/%s' % fname):
            if os.path.getmtime('static/scripts/packed/%s' % fname) > os.path.getmtime('static/scripts/%s' % fname):
                continue # Skip, packed is newer than source.
        d = dict( fname=fname )
        log.info("%(fname)s --> packed/%(fname)s" % d)
        call( cmd % d, shell=True )


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
    # If we're using remote_user authentication, add middleware that
    # protects Galaxy from improperly configured authentication in the
    # upstream server
    if asbool(conf.get( 'use_remote_user', False )):
        from galaxy.web.framework.middleware.remoteuser import RemoteUser
        app = RemoteUser( app, maildomain = conf.get( 'remote_user_maildomain', None ),
                               display_servers = util.listify( conf.get( 'display_servers', '' ) ),
                               admin_users = conf.get( 'admin_users', '' ).split( ',' ) )
        log.debug( "Enabling 'remote user' middleware" )
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
        if asbool( conf.get( 'use_lint', False ) ):
            from paste import lint
            app = lint.make_middleware( app, conf )
            log.debug( "Enabling 'lint' middleware" )
        # Middleware to run the python profiler on each request
        if asbool( conf.get( 'use_profile', False ) ):
            from paste.debug import profile
            app = profile.ProfileMiddleware( app, conf )
            log.debug( "Enabling 'profile' middleware" )
        # Middleware that intercepts print statements and shows them on the
        # returned page
        if asbool( conf.get( 'use_printdebug', True ) ):
            from paste.debug import prints
            app = prints.PrintDebugMiddleware( app, conf )
            log.debug( "Enabling 'print debug' middleware" )
    if debug and asbool( conf.get( 'use_interactive', False ) ):
        # Interactive exception debugging, scary dangerous if publicly
        # accessible, if not enabled we'll use the regular error printing
        # middleware.
        pkg_resources.require( "WebError" )
        from weberror import evalexception
        app = evalexception.EvalException( app, conf,
                                           templating_formatters=build_template_error_formatters() )
        log.debug( "Enabling 'eval exceptions' middleware" )
    else:
        # Not in interactive debug mode, just use the regular error middleware
        if sys.version_info[:2] >= ( 2, 6 ):
            warnings.filterwarnings( 'ignore', '.*', DeprecationWarning, '.*serial_number_generator', 11, True )
            from paste.exceptions import errormiddleware
            warnings.filters.pop()
        else:
            from paste.exceptions import errormiddleware
        app = errormiddleware.ErrorMiddleware( app, conf )
        log.debug( "Enabling 'error' middleware" )
    # Transaction logging (apache access.log style)
    if asbool( conf.get( 'use_translogger', True ) ):
        from framework.middleware.translogger import TransLogger
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
    urlmap["/robots.txt"] = Static( conf.get( "static_robots_txt", 'static/robots.txt'), cache_time )
    # URL mapper becomes the root webapp
    return urlmap
    
def build_template_error_formatters():
    """
    Build a list of template error formatters for WebError. When an error
    occurs, WebError pass the exception to each function in this list until
    one returns a value, which will be displayed on the error page.
    """
    formatters = []
    # Formatter for mako
    import mako.exceptions
    def mako_html_data( exc_value ):
        if isinstance( exc_value, ( mako.exceptions.CompileException, mako.exceptions.SyntaxException ) ):
            return mako.exceptions.html_error_template().render( full=False, css=False )
        if isinstance( exc_value, AttributeError ) and exc_value.args[0].startswith( "'Undefined' object has no attribute" ):
            return mako.exceptions.html_error_template().render( full=False, css=False )
    formatters.append( mako_html_data )
    return formatters
