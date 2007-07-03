import sys, os, atexit

from galaxy import config, db, jobs, util, tools, web
import galaxy.model
import galaxy.model.mapping
import galaxy.datatypes.registry
from galaxy.interfaces import root, tool_runner, proxy, async, admin, user, error, dataset
from galaxy.web import middleware

class UniverseApplication( object ):
    """Encapsulates the state of a Universe application"""
    def __init__( self, **kwargs ):
        print >> sys.stderr, "python path is: " + ", ".join( sys.path )
        # Read config file and check for errors
        self.config = config.Configuration( **kwargs )
        self.config.check()
        config.configure_logging( self.config )
        #Set up datatypes registry
        self.datatypes_registry = galaxy.datatypes.registry.Registry(datatypes = self.config.datatypes)
        galaxy.model.set_datatypes_registry(self.datatypes_registry)
        # Connect up the object model
        if self.config.database_connection:
            self.model = galaxy.model.mapping.init( self.config.file_path,
                                                    self.config.database_connection,
                                                    create_tables = True )
        else:
            self.model = galaxy.model.mapping.init( self.config.file_path,
                                                    "sqlite://%s?isolation_level=IMMEDIATE" % self.config.database,
                                                    create_tables = True )
        # Initialize the tools
        self.toolbox = tools.ToolBox( self.config.tool_config, self.config.tool_path, self )
        # Start the job queue
        self.job_queue = jobs.JobQueue( self )
        self.heartbeat = None
        # Start the heartbeat process if configured and available
        if self.config.use_heartbeat:
            from galaxy import heartbeat
            if heartbeat.Heartbeat:
                self.heartbeat = heartbeat.Heartbeat()
                self.heartbeat.start()
    def shutdown( self ):
        self.job_queue.shutdown()
        if self.heartbeat:
            self.heartbeat.shutdown()
            
def app_factory( global_conf, **kwargs ):
    """
    Return a wsgi application serving the root object
    """
    # Create the application
    if 'app' in kwargs:
        app = kwargs.pop( 'app' )
    else:
        app = UniverseApplication( global_conf = global_conf, **kwargs )
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
    webapp.add_controller( 'dataset', dataset.DatasetInterface( app ) )
    # These two routes handle our simple needs at the moment
    webapp.add_route( '/async/:tool_id/:data_id/:data_secret', controller='async', action='index', tool_id=None, data_id=None, data_secret=None )
    webapp.add_route( '/:controller/:action', action='index' )
    webapp.add_route( '/:action', controller='root', action='index' )
    webapp.finalize_config()
    # Wrap the webapp in some useful middleware
    if kwargs.get( 'middleware', True ):
        webapp = middleware.make_middleware( webapp, global_conf, **kwargs )
    # Close any pooled database connections before forking
    try:
        galaxy.model.mapping.metadata.engine.connection_provider._pool.dispose()
    except:
        pass
    # Return
    return webapp