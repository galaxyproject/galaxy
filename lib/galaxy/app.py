from __future__ import absolute_import
import sys
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
from galaxy.visualization.registry import VisualizationsRegistry
from galaxy.tools.imp_exp import load_history_imp_exp_tools
from galaxy.sample_tracking import external_service_types
from galaxy.openid.providers import OpenIDProviders
from galaxy.tools.data_manager.manager import DataManagers
from galaxy.jobs import metrics as job_metrics
from galaxy.web.proxy import ProxyManager
from galaxy.queue_worker import GalaxyQueueWorker
from tool_shed.galaxy_install import update_repository_manager

import logging
log = logging.getLogger( __name__ )
app = None


class UniverseApplication( object, config.ConfiguresGalaxyMixin ):
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
        self._amqp_internal_connection_obj = galaxy.queues.connection_from_config(self.config)
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
        self.datatypes_registry.load_display_applications()
        # Load datatype converters defined in local datatypes_conf.xml
        self.datatypes_registry.load_datatype_converters( self.toolbox )
        # Load external metadata tool
        self.datatypes_registry.load_external_metadata_tool( self.toolbox )
        # Load history import/export tools.
        load_history_imp_exp_tools( self.toolbox )
        # visualizations registry: associates resources with visualizations, controls how to render
        self.visualizations_registry = VisualizationsRegistry(
            self,
            directories_setting=self.config.visualization_plugins_directory,
            template_cache_dir=self.config.template_cache )
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
        # Start the heartbeat process if configured and available
        if self.config.use_heartbeat:
            from galaxy.util import heartbeat
            if heartbeat.Heartbeat:
                self.heartbeat = heartbeat.Heartbeat( fname=self.config.heartbeat_log )
                self.heartbeat.daemon = True
                self.heartbeat.start()
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

        self.model.engine.dispose()

    def setup_control_queue(self):
        self.control_worker = GalaxyQueueWorker(self, galaxy.queues.control_queue_from_config(self.config),
                                                galaxy.queue_worker.control_message_to_task,
                                                self._amqp_internal_connection_obj)
        self.control_worker.daemon = True
        self.control_worker.start()

    def shutdown( self ):
        self.workflow_scheduling_manager.shutdown()
        self.job_manager.shutdown()
        self.object_store.shutdown()
        if self.heartbeat:
            self.heartbeat.shutdown()
        self.update_repository_manager.shutdown()
        if self.control_worker:
            self.control_worker.shutdown()
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
