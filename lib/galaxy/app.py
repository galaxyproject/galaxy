from __future__ import absolute_import
import logging
import signal
import sys
import time
import os

from galaxy import config, jobs
import galaxy.model
import galaxy.security
import galaxy.queues
from galaxy.managers.collections import DatasetCollectionManager
import galaxy.quota
from galaxy.managers.tags import GalaxyTagManager
from galaxy.visualization.genomes import Genomes
from galaxy.visualization.data_providers.registry import DataProviderRegistry
from galaxy.visualization.plugins.registry import VisualizationsRegistry
from galaxy.tools.special_tools import load_lib_tools
from galaxy.tours import ToursRegistry
from galaxy.webhooks import WebhooksRegistry
from galaxy.sample_tracking import external_service_types
from galaxy.openid.providers import OpenIDProviders
from galaxy.tools.data_manager.manager import DataManagers
from galaxy.jobs import metrics as job_metrics
from galaxy.web.proxy import ProxyManager
from galaxy.queue_worker import GalaxyQueueWorker
from galaxy.util import heartbeat
from galaxy.util.postfork import register_postfork_function
from tool_shed.galaxy_install import update_repository_manager


log = logging.getLogger( __name__ )
app = None


class UniverseApplication( object, config.ConfiguresGalaxyMixin ):
    """Encapsulates the state of a Universe application"""
    def __init__( self, **kwargs ):
        if not log.handlers:
            # Paste didn't handle it, so we need a temporary basic log
            # configured.  The handler added here gets dumped and replaced with
            # an appropriately configured logger in configure_logging below.
            logging.basicConfig(level=logging.DEBUG)
        log.debug( "python path is: %s", ", ".join( sys.path ) )
        self.name = 'galaxy'
        self.new_installation = False
        # Read config file and check for errors
        self.config = config.Configuration( **kwargs )
        self.config.check()
        config.configure_logging( self.config )
        self.configure_fluent_log()
        self.config.reload_sanitize_whitelist(explicit='sanitize_whitelist_file' in kwargs)
        self.amqp_internal_connection_obj = galaxy.queues.connection_from_config(self.config)
        # control_worker *can* be initialized with a queue, but here we don't
        # want to and we'll allow postfork to bind and start it.
        self.control_worker = GalaxyQueueWorker(self)

        self._configure_tool_shed_registry()
        self._configure_object_store( fsmon=True )
        # Setup the database engine and ORM
        config_file = kwargs.get( 'global_conf', {} ).get( '__file__', None )
        if config_file:
            log.debug( 'Using "galaxy.ini" config file: %s', config_file )
        check_migrate_tools = self.config.check_migrate_tools
        self._configure_models( check_migrate_databases=True, check_migrate_tools=check_migrate_tools, config_file=config_file )

        # Manage installed tool shed repositories.
        from tool_shed.galaxy_install import installed_repository_manager
        self.installed_repository_manager = installed_repository_manager.InstalledRepositoryManager( self )

        self._configure_datatypes_registry( self.installed_repository_manager )
        galaxy.model.set_datatypes_registry( self.datatypes_registry )

        # Security helper
        self._configure_security()
        # Tag handler
        self.tag_handler = GalaxyTagManager( self )
        # Dataset Collection Plugins
        self.dataset_collections_service = DatasetCollectionManager(self)

        # Tool Data Tables
        self._configure_tool_data_tables( from_shed_config=False )
        # Load dbkey / genome build manager
        self._configure_genome_builds( data_table_name="__dbkeys__", load_old_style=True )

        # Genomes
        self.genomes = Genomes( self )
        # Data providers registry.
        self.data_provider_registry = DataProviderRegistry()

        # Initialize job metrics manager, needs to be in place before
        # config so per-destination modifications can be made.
        self.job_metrics = job_metrics.JobMetrics( self.config.job_metrics_config_file, app=self )

        # Initialize the job management configuration
        self.job_config = jobs.JobConfiguration(self)

        self._configure_toolbox()

        # Load Data Manager
        self.data_managers = DataManagers( self )
        # Load the update repository manager.
        self.update_repository_manager = update_repository_manager.UpdateRepositoryManager( self )
        # Load proprietary datatype converters and display applications.
        self.installed_repository_manager.load_proprietary_converters_and_display_applications()
        # Load datatype display applications defined in local datatypes_conf.xml
        self.datatypes_registry.load_display_applications( self )
        # Load datatype converters defined in local datatypes_conf.xml
        self.datatypes_registry.load_datatype_converters( self.toolbox )
        # Load external metadata tool
        self.datatypes_registry.load_external_metadata_tool( self.toolbox )
        # Load history import/export tools.
        load_lib_tools( self.toolbox )
        # visualizations registry: associates resources with visualizations, controls how to render
        self.visualizations_registry = VisualizationsRegistry(
            self,
            directories_setting=self.config.visualization_plugins_directory,
            template_cache_dir=self.config.template_cache )
        # Tours registry
        self.tour_registry = ToursRegistry(self.config.tour_config_dir)
        # Webhooks registry
        self.webhooks_registry = WebhooksRegistry(self.config.webhooks_dirs)
        # Load security policy.
        self.security_agent = self.model.security_agent
        self.host_security_agent = galaxy.security.HostAgent(
            model=self.security_agent.model,
            permitted_actions=self.security_agent.permitted_actions )
        # Load quota management.
        if self.config.enable_quotas:
            self.quota_agent = galaxy.quota.QuotaAgent( self.model )
        else:
            self.quota_agent = galaxy.quota.NoQuotaAgent( self.model )
        # Heartbeat for thread profiling
        self.heartbeat = None
        # Container for OpenID authentication routines
        if self.config.enable_openid:
            from galaxy.web.framework import openid_manager
            self.openid_manager = openid_manager.OpenIDManager( self.config.openid_consumer_cache_path )
            self.openid_providers = OpenIDProviders.from_file( self.config.openid_config_file )
        else:
            self.openid_providers = OpenIDProviders()
        from galaxy import auth
        self.auth_manager = auth.AuthManager( self )
        # Start the heartbeat process if configured and available (wait until
        # postfork if using uWSGI)
        if self.config.use_heartbeat:
            if heartbeat.Heartbeat:
                self.heartbeat = heartbeat.Heartbeat(
                    self.config,
                    period=self.config.heartbeat_interval,
                    fname=self.config.heartbeat_log
                )
                self.heartbeat.daemon = True
                register_postfork_function(self.heartbeat.start)
        self.sentry_client = None
        if self.config.sentry_dsn:

            def postfork_sentry_client():
                import raven
                self.sentry_client = raven.Client(self.config.sentry_dsn)

            register_postfork_function(postfork_sentry_client)

        # Transfer manager client
        if self.config.get_bool( 'enable_beta_job_managers', False ):
            from galaxy.jobs import transfer_manager
            self.transfer_manager = transfer_manager.TransferManager( self )
        # Start the job manager
        from galaxy.jobs import manager
        self.job_manager = manager.JobManager( self )
        self.job_manager.start()
        # FIXME: These are exposed directly for backward compatibility
        self.job_queue = self.job_manager.job_queue
        self.job_stop_queue = self.job_manager.job_stop_queue
        self.proxy_manager = ProxyManager( self.config )
        # Initialize the external service types
        self.external_service_types = external_service_types.ExternalServiceTypesCollection(
            self.config.external_service_type_config_file,
            self.config.external_service_type_path, self )

        from galaxy.workflow import scheduling_manager
        # Must be initialized after job_config.
        self.workflow_scheduling_manager = scheduling_manager.WorkflowSchedulingManager( self )

        # Configure handling of signals
        handlers = {}
        if self.heartbeat:
            handlers[signal.SIGUSR1] = self.heartbeat.dump_signal_handler
        self._configure_signal_handlers( handlers )

        self.model.engine.dispose()
        self.server_starttime = int(time.time())  # used for cachebusting

    def shutdown( self ):
        self.workflow_scheduling_manager.shutdown()
        self.job_manager.shutdown()
        self.object_store.shutdown()
        if self.heartbeat:
            self.heartbeat.shutdown()
        self.update_repository_manager.shutdown()
        try:
            self.control_worker.shutdown()
        except AttributeError:
            # There is no control_worker
            pass
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

    def is_job_handler( self ):
        return (self.config.track_jobs_in_database and self.job_config.is_handler(self.config.server_name)) or not self.config.track_jobs_in_database
