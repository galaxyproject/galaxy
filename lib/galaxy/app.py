from __future__ import absolute_import
import sys, os, atexit

from galaxy import config, jobs, util, tools, web
import galaxy.tools.search
import galaxy.tools.data
import tool_shed.galaxy_install
import tool_shed.tool_shed_registry
from galaxy.web import security
import galaxy.model
import galaxy.datatypes.registry
import galaxy.security
from galaxy.objectstore import build_object_store_from_config
import galaxy.quota
from galaxy.tags.tag_handler import GalaxyTagHandler
from galaxy.visualization.genomes import Genomes
from galaxy.visualization.data_providers.registry import DataProviderRegistry
from galaxy.tools.imp_exp import load_history_imp_exp_tools
from galaxy.tools.genome_index import load_genome_index_tools
from galaxy.sample_tracking import external_service_types
from galaxy.openid.providers import OpenIDProviders
from galaxy.tools.data_manager.manager import DataManagers

import logging
log = logging.getLogger( __name__ )

class UniverseApplication( object ):
    """Encapsulates the state of a Universe application"""
    def __init__( self, **kwargs ):
        print >> sys.stderr, "python path is: " + ", ".join( sys.path )
        self.name = 'galaxy'
        self.new_installation = False
        # Read config file and check for errors
        self.config = config.Configuration( **kwargs )
        self.config.check()
        config.configure_logging( self.config )
        self.configure_fluent_log()
        # Determine the database url
        if self.config.database_connection:
            db_url = self.config.database_connection
        else:
            db_url = "sqlite:///%s?isolation_level=IMMEDIATE" % self.config.database
        # Set up the tool sheds registry
        if os.path.isfile( self.config.tool_sheds_config ):
            self.tool_shed_registry = tool_shed.tool_shed_registry.Registry( self.config.root, self.config.tool_sheds_config )
        else:
            self.tool_shed_registry = None
        log.debug( 'self.config.tool_sheds_config: %s, self.tool_shed_registry: %s',
            self.config.tool_sheds_config, self.tool_shed_registry )
        # Initialize database / check for appropriate schema version.  # If this
        # is a new installation, we'll restrict the tool migration messaging.
        from galaxy.model.migrate.check import create_or_verify_database
        create_or_verify_database( db_url, kwargs.get( 'global_conf', {} ).get( '__file__', None ), self.config.database_engine_options, app=self )
        # Alert the Galaxy admin to tools that have been moved from the distribution to the tool shed.
        from tool_shed.galaxy_install.migrate.check import verify_tools
        verify_tools( self, db_url, kwargs.get( 'global_conf', {} ).get( '__file__', None ), self.config.database_engine_options )
        # Object store manager
        self.object_store = build_object_store_from_config(self.config)
        # Setup the database engine and ORM
        from galaxy.model import mapping
        self.model = mapping.init( self.config.file_path,
                                   db_url,
                                   self.config.database_engine_options,
                                   database_query_profiling_proxy = self.config.database_query_profiling_proxy,
                                   object_store = self.object_store,
                                   trace_logger=self.trace_logger )
        # Manage installed tool shed repositories.
        self.installed_repository_manager = tool_shed.galaxy_install.InstalledRepositoryManager( self )
        # Create an empty datatypes registry.
        self.datatypes_registry = galaxy.datatypes.registry.Registry()
        # Load proprietary datatypes defined in datatypes_conf.xml files in all installed tool shed repositories.  We
        # load proprietary datatypes before datatypes in the distribution because Galaxy's default sniffers include some
        # generic sniffers (eg text,xml) which catch anything, so it's impossible for proprietary sniffers to be used.
        # However, if there is a conflict (2 datatypes with the same extension) between a proprietary datatype and a datatype
        # in the Galaxy distribution, the datatype in the Galaxy distribution will take precedence.  If there is a conflict
        # between 2 proprietary datatypes, the datatype from the repository that was installed earliest will take precedence.
        self.installed_repository_manager.load_proprietary_datatypes()
        # Load the data types in the Galaxy distribution, which are defined in self.config.datatypes_config.
        self.datatypes_registry.load_datatypes( self.config.root, self.config.datatypes_config )
        galaxy.model.set_datatypes_registry( self.datatypes_registry )
        # Security helper
        self.security = security.SecurityHelper( id_secret=self.config.id_secret )
        # Tag handler
        self.tag_handler = GalaxyTagHandler()
        # Genomes
        self.genomes = Genomes( self )
        # Data providers registry.
        self.data_provider_registry = DataProviderRegistry()
        # Initialize tool data tables using the config defined by self.config.tool_data_table_config_path.
        self.tool_data_tables = galaxy.tools.data.ToolDataTableManager( tool_data_path=self.config.tool_data_path,
                                                                        config_filename=self.config.tool_data_table_config_path )
        # Load additional entries defined by self.config.shed_tool_data_table_config into tool data tables.
        self.tool_data_tables.load_from_config_file( config_filename=self.config.shed_tool_data_table_config,
                                                     tool_data_path=self.tool_data_tables.tool_data_path,
                                                     from_shed_config=True )
        # Initialize the job management configuration
        self.job_config = jobs.JobConfiguration(self)
        # Initialize the tools, making sure the list of tool configs includes the reserved migrated_tools_conf.xml file.
        tool_configs = self.config.tool_configs
        if self.config.migrated_tools_config not in tool_configs:
            tool_configs.append( self.config.migrated_tools_config )
        self.toolbox = tools.ToolBox( tool_configs, self.config.tool_path, self )
        # Search support for tools
        self.toolbox_search = galaxy.tools.search.ToolBoxSearch( self.toolbox )
        # Load Data Manager
        self.data_managers = DataManagers( self )
        # If enabled, poll respective tool sheds to see if updates are available for any installed tool shed repositories.
        if self.config.get_bool( 'enable_tool_shed_check', False ):
            from tool_shed.galaxy_install import update_manager
            self.update_manager = update_manager.UpdateManager( self )
        # Load proprietary datatype converters and display applications.
        self.installed_repository_manager.load_proprietary_converters_and_display_applications()
        # Load datatype display applications defined in local datatypes_conf.xml
        self.datatypes_registry.load_display_applications()
        # Load datatype converters defined in local datatypes_conf.xml
        self.datatypes_registry.load_datatype_converters( self.toolbox )
        # Load external metadata tool
        self.datatypes_registry.load_external_metadata_tool( self.toolbox )
        # Load history import/export tools.
        load_history_imp_exp_tools( self.toolbox )
        # Load genome indexer tool.
        load_genome_index_tools( self.toolbox )
        # Load security policy.
        self.security_agent = self.model.security_agent
        self.host_security_agent = galaxy.security.HostAgent( model=self.security_agent.model, permitted_actions=self.security_agent.permitted_actions )
        # Load quota management.
        if self.config.enable_quotas:
            self.quota_agent = galaxy.quota.QuotaAgent( self.model )
        else:
            self.quota_agent = galaxy.quota.NoQuotaAgent( self.model )
        # Heartbeat and memdump for thread / heap profiling
        self.heartbeat = None
        self.memdump = None
        self.memory_usage = None
        # Container for OpenID authentication routines
        if self.config.enable_openid:
            from galaxy.web.framework import openid_manager
            self.openid_manager = openid_manager.OpenIDManager( self.config.openid_consumer_cache_path )
            self.openid_providers = OpenIDProviders.from_file( self.config.openid_config )
        else:
            self.openid_providers = OpenIDProviders()
        # Start the heartbeat process if configured and available
        if self.config.use_heartbeat:
            from galaxy.util import heartbeat
            if heartbeat.Heartbeat:
                self.heartbeat = heartbeat.Heartbeat( fname=self.config.heartbeat_log )
                self.heartbeat.start()
        # Enable the memdump signal catcher if configured and available
        if self.config.use_memdump:
            from galaxy.util import memdump
            if memdump.Memdump:
                self.memdump = memdump.Memdump()
        # Transfer manager client
        if self.config.get_bool( 'enable_beta_job_managers', False ):
            from galaxy.jobs import transfer_manager
            self.transfer_manager = transfer_manager.TransferManager( self )
        # Start the job manager
        from galaxy.jobs import manager
        self.job_manager = manager.JobManager( self )
        # FIXME: These are exposed directly for backward compatibility
        self.job_queue = self.job_manager.job_queue
        self.job_stop_queue = self.job_manager.job_stop_queue
        # Initialize the external service types
        self.external_service_types = external_service_types.ExternalServiceTypesCollection( self.config.external_service_type_config_file, self.config.external_service_type_path, self )

    def shutdown( self ):
        self.job_manager.shutdown()
        self.object_store.shutdown()
        if self.heartbeat:
            self.heartbeat.shutdown()
        try:
            # If the datatypes registry was persisted, attempt to
            # remove the temporary file in which it was written.
            if self.datatypes_registry.integrated_datatypes_configs is not None:
                os.unlink( self.datatypes_registry.integrated_datatypes_configs )
        except:
            pass

    def configure_fluent_log( self ):
        if self.config.fluent_log:
            from galaxy.util.log.fluent_log import FluentTraceLogger
            self.trace_logger = FluentTraceLogger( 'galaxy', self.config.fluent_host, self.config.fluent_port ) 
        else:
            self.trace_logger = None
