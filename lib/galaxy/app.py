import logging
import signal
import sys
import time
from typing import Any, Callable, List, Tuple

import galaxy.model
import galaxy.model.security
import galaxy.queues
import galaxy.security
from galaxy import auth, config, jobs
from galaxy.config_watchers import ConfigWatchers
from galaxy.containers import build_container_interfaces
from galaxy.datatypes.registry import Registry
from galaxy.files import ConfiguredFileSources
from galaxy.job_metrics import JobMetrics
from galaxy.managers.api_keys import ApiKeyManager
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.managers.folders import FolderManager
from galaxy.managers.hdas import HDAManager
from galaxy.managers.histories import HistoryManager
from galaxy.managers.interactivetool import InteractiveToolManager
from galaxy.managers.jobs import JobSearch
from galaxy.managers.libraries import LibraryManager
from galaxy.managers.library_datasets import LibraryDatasetsManager
from galaxy.managers.roles import RoleManager
from galaxy.managers.session import GalaxySessionManager
from galaxy.managers.tools import DynamicToolManager
from galaxy.managers.users import UserManager
from galaxy.managers.workflows import (
    WorkflowContentsManager,
    WorkflowsManager,
)
from galaxy.model.base import SharedModelMapping
from galaxy.model.database_heartbeat import DatabaseHeartbeat
from galaxy.model.mapping import GalaxyModelMapping
from galaxy.model.scoped_session import (
    galaxy_scoped_session,
    install_model_scoped_session,
)
from galaxy.model.tags import GalaxyTagHandler
from galaxy.queue_worker import (
    GalaxyQueueWorker,
    send_local_control_task,
)
from galaxy.quota import get_quota_agent, QuotaAgent
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.tool_shed.galaxy_install.installed_repository_manager import InstalledRepositoryManager
from galaxy.tool_shed.galaxy_install.update_repository_manager import UpdateRepositoryManager
from galaxy.tool_util.deps.views import DependencyResolversView
from galaxy.tool_util.verify.test_data import TestDataResolver
from galaxy.tools.cache import (
    ToolCache,
    ToolShedRepositoryCache
)
from galaxy.tools.data_manager.manager import DataManagers
from galaxy.tools.error_reports import ErrorReports
from galaxy.tools.special_tools import load_lib_tools
from galaxy.tours import build_tours_registry, ToursRegistry
from galaxy.util import (
    ExecutionTimer,
    heartbeat,
    StructuredExecutionTimer,
)
from galaxy.util.task import IntervalTask
from galaxy.visualization.data_providers.registry import DataProviderRegistry
from galaxy.visualization.genomes import Genomes
from galaxy.visualization.plugins.registry import VisualizationsRegistry
from galaxy.web import url_for
from galaxy.web.proxy import ProxyManager
from galaxy.web_stack import application_stack_instance, ApplicationStack
from galaxy.webhooks import WebhooksRegistry
from galaxy.workflow.trs_proxy import TrsProxy
from .di import Container
from .structured_app import BasicSharedApp, MinimalManagerApp, StructuredApp

log = logging.getLogger(__name__)
app = None


class HaltableContainer(Container):
    haltables: List[Tuple[str, Callable]]

    def __init__(self) -> None:
        super().__init__()
        self.haltables = []

    def shutdown(self):
        exception = None
        for what, haltable in self.haltables:
            try:
                haltable()
            except Exception as e:
                log.exception(f"Failed to shutdown {what} cleanly")
                exception = exception or e
        if exception is not None:
            raise exception


class MinimalGalaxyApplication(BasicSharedApp, config.ConfiguresGalaxyMixin, HaltableContainer):
    """Encapsulates the state of a minimal Galaxy application"""

    def __init__(self, fsmon=False, configure_logging=True, **kwargs) -> None:
        super().__init__()
        self.haltables = [
            ("object store", self._shutdown_object_store),
            ("database connection", self._shutdown_model),
        ]
        self._register_singleton(BasicSharedApp, self)
        if not log.handlers:
            # Paste didn't handle it, so we need a temporary basic log
            # configured.  The handler added here gets dumped and replaced with
            # an appropriately configured logger in configure_logging below.
            logging.basicConfig(level=logging.DEBUG)
        log.debug("python path is: %s", ", ".join(sys.path))
        self.name = 'galaxy'
        self.is_webapp = False
        self.new_installation = False
        # Read config file and check for errors
        self.config: Any = self._register_singleton(config.Configuration, config.Configuration(**kwargs))
        self.config.check()
        if configure_logging:
            config.configure_logging(self.config)
        self._configure_object_store(fsmon=True)
        config_file = kwargs.get('global_conf', {}).get('__file__', None)
        if config_file:
            log.debug('Using "galaxy.ini" config file: %s', config_file)
        check_migrate_tools = self.config.check_migrate_tools
        self._configure_models(check_migrate_databases=self.config.check_migrate_databases, check_migrate_tools=check_migrate_tools, config_file=config_file)
        # Security helper
        self._configure_security()
        self._register_singleton(IdEncodingHelper, self.security)
        self._register_singleton(SharedModelMapping, self.model)
        self._register_singleton(GalaxyModelMapping, self.model)
        self._register_singleton(galaxy_scoped_session, self.model.context)
        self._register_singleton(install_model_scoped_session, self.install_model.context)

    def configure_fluent_log(self):
        if self.config.fluent_log:
            from galaxy.util.custom_logging.fluent_log import FluentTraceLogger
            self.trace_logger = FluentTraceLogger('galaxy', self.config.fluent_host, self.config.fluent_port)
        else:
            self.trace_logger = None

    def _shutdown_object_store(self):
        self.object_store.shutdown()

    def _shutdown_model(self):
        self.model.engine.dispose()


class GalaxyManagerApplication(MinimalManagerApp, MinimalGalaxyApplication):
    """Extends the MinimalGalaxyApplication with most managers that are not tied to a web or job handling context."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._register_singleton(MinimalManagerApp, self)
        self.execution_timer_factory = self._register_singleton(ExecutionTimerFactory, ExecutionTimerFactory(self.config))
        self.configure_fluent_log()
        self.application_stack = self._register_singleton(ApplicationStack, application_stack_instance(app=self))
        # Initialize job metrics manager, needs to be in place before
        # config so per-destination modifications can be made.
        self.job_metrics = self._register_singleton(JobMetrics, JobMetrics(self.config.job_metrics_config_file, app=self))
        # Initialize the job management configuration
        self.job_config = self._register_singleton(jobs.JobConfiguration)

        # Tag handler
        self.tag_handler = self._register_singleton(GalaxyTagHandler)
        self.user_manager = self._register_singleton(UserManager)
        self._register_singleton(GalaxySessionManager)
        self.hda_manager = self._register_singleton(HDAManager)
        self.history_manager = self._register_singleton(HistoryManager)
        self.job_search = self._register_singleton(JobSearch)
        self.dataset_collection_manager = self._register_singleton(DatasetCollectionManager)
        self.workflow_manager = self._register_singleton(WorkflowsManager)
        self.workflow_contents_manager = self._register_singleton(WorkflowContentsManager)
        self.library_folder_manager = self._register_singleton(FolderManager)
        self.library_manager = self._register_singleton(LibraryManager)
        self.library_datasets_manager = self._register_singleton(LibraryDatasetsManager)
        self.role_manager = self._register_singleton(RoleManager)
        from galaxy.jobs.manager import JobManager
        self.job_manager = self._register_singleton(JobManager)

        # ConfiguredFileSources
        self.file_sources = self._register_singleton(ConfiguredFileSources, ConfiguredFileSources.from_app_config(self.config))

        # We need the datatype registry for running certain tasks that modify HDAs, and to build the registry we need
        # to setup the installed repositories ... this is not ideal
        self._configure_tool_config_files()
        self.installed_repository_manager = self._register_singleton(InstalledRepositoryManager, InstalledRepositoryManager(self))
        self._configure_datatypes_registry(self.installed_repository_manager)
        self._register_singleton(Registry, self.datatypes_registry)
        galaxy.model.set_datatypes_registry(self.datatypes_registry)

        self.sentry_client = None
        if self.config.sentry_dsn:
            event_level = self.config.sentry_event_level.upper()
            assert event_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], f"Invalid sentry event level '{self.config.sentry.event_level}'"

            def postfork_sentry_client():
                import sentry_sdk
                from sentry_sdk.integrations.logging import LoggingIntegration

                sentry_logging = LoggingIntegration(
                    level=logging.INFO,  # Capture info and above as breadcrumbs
                    event_level=getattr(logging, event_level)  # Send errors as events
                )
                self.sentry_client = sentry_sdk.init(
                    self.config.sentry_dsn,
                    release=f"{self.config.version_major}.{self.config.version_minor}",
                    integrations=[sentry_logging]
                )

            self.application_stack.register_postfork_function(postfork_sentry_client)


class UniverseApplication(StructuredApp, GalaxyManagerApplication):
    """Encapsulates the state of a Universe application"""

    def __init__(self, **kwargs) -> None:
        startup_timer = ExecutionTimer()
        super().__init__(fsmon=True, **kwargs)
        self.haltables = [
            ("queue worker", self._shutdown_queue_worker),
            ("file watcher", self._shutdown_watcher),
            ("database heartbeat", self._shutdown_database_heartbeat),
            ("workflow scheduler", self._shutdown_scheduling_manager),
            ("object store", self._shutdown_object_store),
            ("job manager", self._shutdown_job_manager),
            ("application heartbeat", self._shutdown_heartbeat),
            ("repository manager", self._shutdown_repo_manager),
            ("database connection repository cache", self._shutdown_repo_cache),
            ("database connection", self._shutdown_model),
            ("application stack", self._shutdown_application_stack),
        ]
        self._register_singleton(StructuredApp, self)
        # A lot of postfork initialization depends on the server name, ensure it is set immediately after forking before other postfork functions
        self.application_stack.register_postfork_function(self.application_stack.set_postfork_server_name, self)
        self.config.reload_sanitize_allowlist(explicit='sanitize_allowlist_file' in kwargs)
        self.amqp_internal_connection_obj = galaxy.queues.connection_from_config(self.config)
        # queue_worker *can* be initialized with a queue, but here we don't
        # want to and we'll allow postfork to bind and start it.
        self.queue_worker = self._register_singleton(GalaxyQueueWorker, GalaxyQueueWorker(self))

        self._configure_tool_shed_registry()

        self.dependency_resolvers_view = self._register_singleton(DependencyResolversView, DependencyResolversView(self))
        self.test_data_resolver = self._register_singleton(TestDataResolver, TestDataResolver(file_dirs=self.config.tool_test_data_directories))
        self.dynamic_tool_manager = self._register_singleton(DynamicToolManager)
        self.api_keys_manager = self._register_singleton(ApiKeyManager)

        # Tool Data Tables
        self._configure_tool_data_tables(from_shed_config=False)
        # Load dbkey / genome build manager
        self._configure_genome_builds(data_table_name="__dbkeys__", load_old_style=True)

        # Genomes
        self.genomes = self._register_singleton(Genomes)
        # Data providers registry.
        self.data_provider_registry = self._register_singleton(DataProviderRegistry)

        # Initialize error report plugins.
        self.error_reports = self._register_singleton(ErrorReports, ErrorReports(self.config.error_report_file, app=self))

        # Setup a Tool Cache
        self.tool_cache = self._register_singleton(ToolCache)
        self.tool_shed_repository_cache = self._register_singleton(ToolShedRepositoryCache)
        # Watch various config files for immediate reload
        self.watchers = self._register_singleton(ConfigWatchers)
        self._configure_toolbox()
        # Load Data Manager
        self.data_managers = self._register_singleton(DataManagers)
        # Load the update repository manager.
        self.update_repository_manager = self._register_singleton(UpdateRepositoryManager, UpdateRepositoryManager(self))
        # Load proprietary datatype converters and display applications.
        self.installed_repository_manager.load_proprietary_converters_and_display_applications()
        # Load datatype display applications defined in local datatypes_conf.xml
        self.datatypes_registry.load_display_applications(self)
        # Load datatype converters defined in local datatypes_conf.xml
        self.datatypes_registry.load_datatype_converters(self.toolbox)
        # Load external metadata tool
        self.datatypes_registry.load_external_metadata_tool(self.toolbox)
        # Load history import/export tools.
        load_lib_tools(self.toolbox)
        self.toolbox.persist_cache(register_postfork=True)
        # visualizations registry: associates resources with visualizations, controls how to render
        self.visualizations_registry = self._register_singleton(VisualizationsRegistry, VisualizationsRegistry(
            self,
            directories_setting=self.config.visualization_plugins_directory,
            template_cache_dir=self.config.template_cache_path))
        # Tours registry
        tour_registry = build_tours_registry(self.config.tour_config_dir)
        self.tour_registry = tour_registry
        self[ToursRegistry] = tour_registry  # type: ignore[misc]
        # Webhooks registry
        self.webhooks_registry = self._register_singleton(WebhooksRegistry, WebhooksRegistry(self.config.webhooks_dir))
        # Load security policy.
        self.security_agent = self.model.security_agent
        self.host_security_agent = galaxy.model.security.HostAgent(
            model=self.security_agent.model,
            permitted_actions=self.security_agent.permitted_actions)
        # Load quota management.
        self.quota_agent = self._register_singleton(QuotaAgent, get_quota_agent(self.config, self.model))
        # Heartbeat for thread profiling
        self.heartbeat = None
        self.auth_manager = self._register_singleton(auth.AuthManager, auth.AuthManager(self.config))
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
                self.application_stack.register_postfork_function(self.heartbeat.start)

        self.authnz_manager = None
        if self.config.enable_oidc:
            from galaxy.authnz import managers
            self.authnz_manager = managers.AuthnzManager(self,
                                                         self.config.oidc_config_file,
                                                         self.config.oidc_backends_config_file)

        self.containers = {}
        if self.config.enable_beta_containers_interface:
            self.containers = build_container_interfaces(
                self.config.containers_config_file,
                containers_conf=self.config.containers_conf
            )

        if not self.config.enable_celery_tasks and self.config.history_audit_table_prune_interval > 0:
            self.prune_history_audit_task = IntervalTask(
                func=lambda: galaxy.model.HistoryAudit.prune(self.model.session),
                name="HistoryAuditTablePruneTask",
                interval=self.config.history_audit_table_prune_interval,
                immediate_start=False,
                time_execution=True)
            self.application_stack.register_postfork_function(self.prune_history_audit_task.start)
            self.haltables.append(("HistoryAuditTablePruneTask", self.prune_history_audit_task.shutdown))
        # Start the job manager
        self.application_stack.register_postfork_function(self.job_manager.start)
        # If app is not job handler but uses mule messaging.
        # Can be removed when removing mule support.
        self.job_manager._check_jobs_at_startup()
        self.proxy_manager = ProxyManager(self.config)

        from galaxy.workflow import scheduling_manager
        # Must be initialized after job_config.
        self.workflow_scheduling_manager = scheduling_manager.WorkflowSchedulingManager(self)

        self.trs_proxy = self._register_singleton(TrsProxy, TrsProxy(self.config))
        # Must be initialized after any component that might make use of stack messaging is configured. Alternatively if
        # it becomes more commonly needed we could create a prefork function registration method like we do with
        # postfork functions.
        self.application_stack.init_late_prefork()

        self.interactivetool_manager = InteractiveToolManager(self)

        # Configure handling of signals
        handlers = {}
        if self.heartbeat:
            handlers[signal.SIGUSR1] = self.heartbeat.dump_signal_handler
        self._configure_signal_handlers(handlers)

        self.database_heartbeat = DatabaseHeartbeat(
            application_stack=self.application_stack
        )
        self.database_heartbeat.add_change_callback(self.watchers.change_state)
        self.application_stack.register_postfork_function(self.database_heartbeat.start)

        # Start web stack message handling
        self.application_stack.register_postfork_function(self.application_stack.start)
        self.application_stack.register_postfork_function(self.queue_worker.bind_and_start)
        # Delay toolbox index until after startup
        self.application_stack.register_postfork_function(lambda: send_local_control_task(self, 'rebuild_toolbox_search_index'))

        # Inject url_for for components to more easily optionally depend
        # on url_for.
        self.url_for = url_for

        self.server_starttime = int(time.time())  # used for cachebusting
        log.info(f"Galaxy app startup finished {startup_timer}")

    def _shutdown_queue_worker(self):
        self.queue_worker.shutdown()

    def _shutdown_watcher(self):
        self.watchers.shutdown()

    def _shutdown_database_heartbeat(self):
        self.database_heartbeat.shutdown()

    def _shutdown_scheduling_manager(self):
        self.workflow_scheduling_manager.shutdown()

    def _shutdown_job_manager(self):
        self.job_manager.shutdown()

    def _shutdown_heartbeat(self):
        if self.heartbeat:
            self.heartbeat.shutdown()

    def _shutdown_repo_manager(self):
        self.update_repository_manager.shutdown()

    def _shutdown_repo_cache(self):
        self.tool_shed_repository_cache.shutdown()

    def _shutdown_application_stack(self):
        self.application_stack.shutdown()

    @property
    def is_job_handler(self) -> bool:
        return (self.config.track_jobs_in_database and self.job_config.is_handler) or not self.config.track_jobs_in_database


class StatsdStructuredExecutionTimer(StructuredExecutionTimer):

    def __init__(self, galaxy_statsd_client, *args, **kwds):
        self.galaxy_statsd_client = galaxy_statsd_client
        super().__init__(*args, **kwds)

    def to_str(self, **kwd):
        self.galaxy_statsd_client.timing(self.timer_id, self.elapsed * 1000., kwd)
        return super().to_str(**kwd)


class ExecutionTimerFactory:

    def __init__(self, config):
        statsd_host = getattr(config, "statsd_host", None)
        if statsd_host:
            from galaxy.web.framework.middleware.statsd import GalaxyStatsdClient
            self.galaxy_statsd_client = GalaxyStatsdClient(
                statsd_host,
                getattr(config, 'statsd_port', 8125),
                getattr(config, 'statsd_prefix', 'galaxy'),
                getattr(config, 'statsd_influxdb', False),
                getattr(config, 'statsd_mock_calls', False),
            )
        else:
            self.galaxy_statsd_client = None

    def get_timer(self, *args, **kwd):
        if self.galaxy_statsd_client:
            return StatsdStructuredExecutionTimer(self.galaxy_statsd_client, *args, **kwd)
        else:
            return StructuredExecutionTimer(*args, **kwd)
