import sys, os, atexit

from galaxy import config, db, jobs, util, tools, web
import galaxy.model.mapping
from galaxy.interfaces import root, tool_runner, proxy, async, admin, user, error
from galaxy.web import middleware
from galaxy.app import UniverseApplication

def app_factory( global_conf, **kwargs ):
    """
    Return a wsgi application serving the root object
    """
    # Create the application
    if 'app' in kwargs:
        app = kwargs.pop( 'app' )
    else:
        app = UniverseApplication( **kwargs )
    atexit.register( app.shutdown )
    # Create the universe WSGI application
    webapp = web.framework.WebApplication()
    # Transaction that provides access to unvierse history
    webapp.set_transaction_factory( lambda e: web.UniverseWebTransaction( e, app ) )
    # Add controllers to the web application
    webapp.add_controller( 'root', root.Universe( app ) )
    webapp.add_controller( 'tool_runner', tool_runner.ToolRunner( app ) )
    webapp.add_controller( 'ucsc_proxy', proxy.UCSCProxy( app ) )
    webapp.add_controller( 'async', async.ASync( app ) )
    webapp.add_controller( 'admin', admin.Admin( app ) )
    webapp.add_controller( 'user', user.User( app ) )
    webapp.add_controller( 'error', error.Error( app ) )
    # These two routes handle our simple needs at the moment
    webapp.add_route( '/async/:tool_id/:data_id', controller='async', action='index', tool_id=None, data_id=None )
    webapp.add_route( '/:controller/:action', action='index' )
    webapp.add_route( '/:action', controller='root', action='index' )
    webapp.finalize_config()
    # Wrap the webapp in some useful middleware
    if kwargs.get( 'middleware', True ):
        webapp = middleware.make_middleware( webapp, global_conf, **kwargs )
    return webapp
