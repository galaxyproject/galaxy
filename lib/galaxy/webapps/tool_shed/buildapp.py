"""
Provides factory methods to assemble the Galaxy web application
"""
import atexit
import config
import logging
import os
import sys

from inspect import isclass

from paste.request import parse_formvars
from paste.util import import_string
from paste import httpexceptions
from galaxy.util import asbool

import pkg_resources

import galaxy.webapps.tool_shed.model
import galaxy.webapps.tool_shed.model.mapping
import galaxy.web.framework.webapp
from galaxy.webapps.tool_shed.framework.middleware import hg
from galaxy import util

log = logging.getLogger( __name__ )

class CommunityWebApplication( galaxy.web.framework.webapp.WebApplication ):
    pass

def add_ui_controllers( webapp, app ):
    """
    Search for controllers in the 'galaxy.webapps.controllers' module and add
    them to the webapp.
    """
    from galaxy.web.base.controller import BaseUIController
    from galaxy.web.base.controller import ControllerUnavailable
    import galaxy.webapps.tool_shed.controllers
    controller_dir = galaxy.webapps.tool_shed.controllers.__path__[0]
    for fname in os.listdir( controller_dir ):
        if not fname.startswith( "_" ) and fname.endswith( ".py" ):
            name = fname[:-3]
            module_name = "galaxy.webapps.tool_shed.controllers." + name
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
    # Create the Galaxy tool shed application unless passed in
    if 'app' in kwargs:
        app = kwargs.pop( 'app' )
    else:
        try:
            from galaxy.webapps.tool_shed.app import UniverseApplication
            app = UniverseApplication( global_conf=global_conf, **kwargs )
        except:
            import traceback, sys
            traceback.print_exc()
            sys.exit( 1 )
    atexit.register( app.shutdown )
    # Create the universe WSGI application
    webapp = CommunityWebApplication( app, session_cookie='galaxycommunitysession', name="tool_shed" )
    add_ui_controllers( webapp, app )
    webapp.add_route( '/view/{owner}', controller='repository', action='sharable_owner' )
    webapp.add_route( '/view/{owner}/{name}', controller='repository', action='sharable_repository' )
    webapp.add_route( '/view/{owner}/{name}/{changeset_revision}', controller='repository', action='sharable_repository_revision' )
    # Handle displaying tool help images and README file images for tools contained in repositories.
    webapp.add_route( '/repository/static/images/:repository_id/:image_file',
                      controller='repository',
                      action='display_image_in_repository',
                      repository_id=None,
                      image_file=None )
    webapp.add_route( '/:controller/:action', action='index' )
    webapp.add_route( '/:action', controller='repository', action='index' )
    webapp.add_route( '/repos/*path_info', controller='hg', action='handle_request', path_info='/' )
    # Add the web API.  # A good resource for RESTful services - http://routes.readthedocs.org/en/latest/restful.html
    webapp.add_api_controllers( 'galaxy.webapps.tool_shed.api', app )
    webapp.mapper.connect( 'api_key_retrieval',
                           '/api/authenticate/baseauth/',
                           controller='authenticate',
                           action='get_tool_shed_api_key',
                           conditions=dict( method=[ "GET" ] ) )
    webapp.mapper.resource( 'category',
                            'categories',
                            controller='categories',
                            name_prefix='category_',
                            path_prefix='/api',
                            parent_resources=dict( member_name='category', collection_name='categories' ) )
    webapp.mapper.resource( 'repository',
                            'repositories',
                            controller='repositories',
                            collection={ 'add_repository_registry_entry' : 'POST',
                                         'get_repository_revision_install_info' : 'GET',
                                         'get_ordered_installable_revisions' : 'GET',
                                         'remove_repository_registry_entry' : 'POST',
                                         'repository_ids_for_setting_metadata' : 'GET',
                                         'reset_metadata_on_repositories' : 'POST',
                                         'reset_metadata_on_repository' : 'POST' },
                            name_prefix='repository_',
                            path_prefix='/api',
                            new={ 'import_capsule' : 'POST' },
                            parent_resources=dict( member_name='repository', collection_name='repositories' ) )
    webapp.mapper.resource( 'repository_revision',
                            'repository_revisions',
                            member={ 'repository_dependencies' : 'GET',
                                     'export' : 'POST' },
                            controller='repository_revisions',
                            name_prefix='repository_revision_',
                            path_prefix='/api',
                            parent_resources=dict( member_name='repository_revision', collection_name='repository_revisions' ) )
    webapp.mapper.resource( 'user',
                            'users',
                            controller='users',
                            name_prefix='user_',
                            path_prefix='/api',
                            parent_resources=dict( member_name='user', collection_name='users' ) )
    webapp.finalize_config()
    # Wrap the webapp in some useful middleware
    if kwargs.get( 'middleware', True ):
        webapp = wrap_in_middleware( webapp, global_conf, **kwargs )
    if kwargs.get( 'static_enabled', True ):
        webapp = wrap_in_static( webapp, global_conf, **kwargs )
    # Close any pooled database connections before forking
    try:
        galaxy.webapps.tool_shed.model.mapping.metadata.engine.connection_provider._pool.dispose()
    except:
        pass
    # Return
    return webapp

def wrap_in_middleware( app, global_conf, **local_conf ):
    """Based on the configuration wrap `app` in a set of common and useful middleware."""
    # Merge the global and local configurations
    conf = global_conf.copy()
    conf.update( local_conf )
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
        from galaxy.webapps.tool_shed.framework.middleware.remoteuser import RemoteUser
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
        import galaxy.web.framework.middleware.error
        app = galaxy.web.framework.middleware.error.ErrorMiddleware( app, conf )
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
    app = hg.Hg( app, conf )
    log.debug( "Enabling hg middleware" )
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
    urlmap["/static"] = Static( conf.get( "static_dir", "./static/" ), cache_time )
    urlmap["/images"] = Static( conf.get( "static_images_dir", "./static/images" ), cache_time )
    urlmap["/static/scripts"] = Static( conf.get( "static_scripts_dir", "./static/scripts/" ), cache_time )
    urlmap["/static/style"] = Static( conf.get( "static_style_dir", "./static/style/blue" ), cache_time )
    urlmap["/favicon.ico"] = Static( conf.get( "static_favicon_dir", "./static/favicon.ico" ), cache_time )
    urlmap["/robots.txt"] = Static( conf.get( "static_robots_txt", "./static/robots.txt" ), cache_time )
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
