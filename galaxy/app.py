from galaxy import config, tools, jobs, web
import galaxy.model.mapping

class UniverseApplication( object ):
    """Encapsulates the state of a Universe application"""
    def __init__( self, **kwargs ):
        # Read config file and check for errors
        self.config = config.Configuration( **kwargs )
        self.config.check()
        config.configure_logging( self.config )
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
        self.toolbox = tools.ToolBox( self.config.tool_config, self.config.tool_path )
        # Start the job queue
        self.job_queue = jobs.JobQueue( self.config.job_queue_workers, self )
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