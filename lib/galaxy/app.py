import sys, os, atexit

from galaxy import config, jobs, util, tools, web
from galaxy.tracks import store
from galaxy.web import security
import galaxy.model
import galaxy.model.mapping
import galaxy.datatypes.registry
import galaxy.security

class UniverseApplication( object ):
    """Encapsulates the state of a Universe application"""
    def __init__( self, **kwargs ):
        print >> sys.stderr, "python path is: " + ", ".join( sys.path )
        # Read config file and check for errors
        self.config = config.Configuration( **kwargs )
        self.config.check()
        config.configure_logging( self.config )
        # Set up datatypes registry
        self.datatypes_registry = galaxy.datatypes.registry.Registry( self.config.root, self.config.datatypes_config )
        galaxy.model.set_datatypes_registry( self.datatypes_registry )
        # Determine the database url
        if self.config.database_connection:
            db_url = self.config.database_connection
        else:
            db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % self.config.database
        # Setup the database engine and ORM
        self.model = galaxy.model.mapping.init( self.config.file_path,
                                                db_url,
                                                self.config.database_engine_options,
                                                create_tables = self.config.database_create_tables )
        # Security helper
        self.security = security.SecurityHelper( id_secret=self.config.id_secret )
        # Initialize the tools
        self.toolbox = tools.ToolBox( self.config.tool_config, self.config.tool_path, self )
        # Load datatype converters
        self.datatypes_registry.load_datatype_converters( self.toolbox )
        # Load datatype indexers
        self.datatypes_registry.load_datatype_indexers( self.toolbox )
        #Load security policy
        self.security_agent = self.model.security_agent
        # Heartbeat and memdump for thread / heap profiling
        self.heartbeat = None
        self.memdump = None
        self.memory_usage = None
        # Start the heartbeat process if configured and available
        if self.config.use_heartbeat:
            from galaxy.util import heartbeat
            if heartbeat.Heartbeat:
                self.heartbeat = heartbeat.Heartbeat()
                self.heartbeat.start()
        # Enable the memdump signal catcher if configured and available
        if self.config.use_memdump:
            from galaxy.util import memdump
            if memdump.Memdump:
                self.memdump = memdump.Memdump()
        # Enable memory_usage logging if configured
        if self.config.log_memory_usage:
            from galaxy.util import memory_usage
            self.memory_usage = memory_usage
        # Start the job queue
        self.job_manager = jobs.JobManager( self )
        # FIXME: These are exposed directly for backward compatibility
        self.job_queue = self.job_manager.job_queue
        self.job_stop_queue = self.job_manager.job_stop_queue
        # Track Store
        self.track_store = store.TrackStoreManager( self.config.track_store_path )
        
    def shutdown( self ):
        self.job_manager.shutdown()
        if self.heartbeat:
            self.heartbeat.shutdown()
