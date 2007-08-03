import sys, os, atexit

from galaxy import config, jobs, util, tools, web
import galaxy.model
import galaxy.model.mapping
import galaxy.datatypes.registry

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
        #Load datatype converters
        self.datatypes_registry.load_datatype_converters(self.config.datatype_converters_config, self.config.datatype_converters_path, self.toolbox)
        # Start the job queue
        self.job_queue = jobs.JobQueue( self )
        self.heartbeat = None
        # Start the heartbeat process if configured and available
        if self.config.use_heartbeat:
            from galaxy.util import heartbeat
            if heartbeat.Heartbeat:
                self.heartbeat = heartbeat.Heartbeat()
                self.heartbeat.start()
    def shutdown( self ):
        self.job_queue.shutdown()
        if self.heartbeat:
            self.heartbeat.shutdown()
