import collections
import errno
import logging
import os
import signal
import sys
import threading
import time
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
)

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

import galaxy.model
import galaxy.model.security
import galaxy.queues
import galaxy.security
from galaxy import (
    auth,
    config,
    jobs,
    tools,
)
from galaxy.carbon_emissions import get_carbon_intensity_entry
from galaxy.celery.base_task import (
    GalaxyTaskBeforeStart,
    GalaxyTaskBeforeStartUserRateLimitPostgres,
    GalaxyTaskBeforeStartUserRateLimitStandard,
)
from galaxy.config import GalaxyAppConfiguration
from galaxy.config_watchers import ConfigWatchers
from galaxy.datatypes.registry import Registry
from galaxy.files import (
    ConfiguredFileSources,
    ConfiguredFileSourcesConf,
    UserDefinedFileSources,
)
from galaxy.files.plugins import (
    FileSourcePluginLoader,
    FileSourcePluginsConfig,
)
from galaxy.files.templates import ConfiguredFileSourceTemplates
from galaxy.job_metrics import JobMetrics
from galaxy.jobs.manager import JobManager
from galaxy.managers.api_keys import ApiKeyManager
from galaxy.managers.citations import CitationsManager
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.managers.dbkeys import GenomeBuilds
from galaxy.managers.file_source_instances import (
    FileSourceInstancesManager,
    UserDefinedFileSourcesConfig,
    UserDefinedFileSourcesImpl,
)
from galaxy.managers.folders import FolderManager
from galaxy.managers.hdas import HDAManager
from galaxy.managers.histories import HistoryManager
from galaxy.managers.interactivetool import InteractiveToolManager
from galaxy.managers.jobs import JobSearch
from galaxy.managers.libraries import LibraryManager
from galaxy.managers.library_datasets import LibraryDatasetsManager
from galaxy.managers.notification import NotificationManager
from galaxy.managers.object_store_instances import UserObjectStoreResolverImpl
from galaxy.managers.roles import RoleManager
from galaxy.managers.session import GalaxySessionManager
from galaxy.managers.tasks import (
    AsyncTasksManager,
    CeleryAsyncTasksManager,
)
from galaxy.managers.tools import DynamicToolManager
from galaxy.managers.users import UserManager
from galaxy.managers.workflows import (
    WorkflowContentsManager,
    WorkflowsManager,
)
from galaxy.model import (
    custom_types,
    mapping,
)
from galaxy.model.base import (
    ModelMapping,
    SharedModelMapping,
)
from galaxy.model.database_heartbeat import DatabaseHeartbeat
from galaxy.model.database_utils import (
    database_exists,
    is_one_database,
    is_postgres,
)
from galaxy.model.mapping import GalaxyModelMapping
from galaxy.model.migrations import verify_databases
from galaxy.model.orm.engine_factory import build_engine
from galaxy.model.scoped_session import (
    galaxy_scoped_session,
    install_model_scoped_session,
)
from galaxy.model.tags import GalaxyTagHandler
from galaxy.model.tool_shed_install import (
    HasToolBox,
    mapping as install_mapping,
)
from galaxy.objectstore import (
    BaseObjectStore,
    build_object_store_from_config,
    UserObjectStoreResolver,
    UserObjectStoresAppConfig,
)
from galaxy.objectstore.templates import ConfiguredObjectStoreTemplates
from galaxy.queue_worker import (
    GalaxyQueueWorker,
    reload_toolbox,
    send_local_control_task,
)
from galaxy.quota import (
    get_quota_agent,
    QuotaAgent,
)
from galaxy.schema.fields import Security
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.security.vault import (
    is_vault_configured,
    Vault,
    VaultFactory,
)
from galaxy.short_term_storage import (
    ShortTermStorageAllocator,
    ShortTermStorageConfiguration,
    ShortTermStorageManager,
    ShortTermStorageMonitor,
)
from galaxy.tool_shed.cache import ToolShedRepositoryCache
from galaxy.tool_shed.galaxy_install.client import InstallationTarget
from galaxy.tool_shed.galaxy_install.installed_repository_manager import InstalledRepositoryManager
from galaxy.tool_shed.galaxy_install.update_repository_manager import UpdateRepositoryManager
from galaxy.tool_util.data import ToolDataTableManager as BaseToolDataTableManager
from galaxy.tool_util.deps import containers
from galaxy.tool_util.deps.dependencies import AppInfo
from galaxy.tool_util.deps.views import DependencyResolversView
from galaxy.tool_util.verify.test_data import TestDataResolver
from galaxy.tools.biotools import get_galaxy_biotools_metadata_source
from galaxy.tools.cache import ToolCache
from galaxy.tools.data import ToolDataTableManager
from galaxy.tools.data_manager.manager import DataManagers
from galaxy.tools.error_reports import ErrorReports
from galaxy.tools.evaluation import ToolTemplatingException
from galaxy.tools.search import ToolBoxSearch
from galaxy.tools.special_tools import load_lib_tools
from galaxy.tours import (
    build_tours_registry,
    ToursRegistry,
)
from galaxy.util import (
    ExecutionTimer,
    heartbeat,
    listify,
    StructuredExecutionTimer,
)
from galaxy.util.task import IntervalTask
from galaxy.util.tool_shed import tool_shed_registry
from galaxy.visualization.data_providers.registry import DataProviderRegistry
from galaxy.visualization.genomes import Genomes
from galaxy.visualization.plugins.registry import VisualizationsRegistry
from galaxy.web import url_for
from galaxy.web.framework.base import server_starttime
from galaxy.web.proxy import ProxyManager
from galaxy.web_stack import (
    application_stack_instance,
    ApplicationStack,
)
from galaxy.webhooks import WebhooksRegistry
from galaxy.workflow import scheduling_manager
from galaxy.workflow.trs_proxy import TrsProxy
from .di import Container
from .structured_app import (
    BasicSharedApp,
    MinimalManagerApp,
    StructuredApp,
)

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


class SentryClientMixin:
    config: GalaxyAppConfiguration
    application_stack: ApplicationStack

    def configure_sentry_client(self):
        self.sentry_client = None
        if self.config.sentry_dsn:
            event_level = self.config.sentry_event_level.upper()
            assert event_level in [
                "DEBUG",
                "INFO",
                "WARNING",
                "ERROR",
                "CRITICAL",
            ], f"Invalid sentry event level '{self.config.sentry.event_level}'"

            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration

            sentry_logging = LoggingIntegration(
                level=logging.INFO,  # Capture info and above as breadcrumbs
                event_level=getattr(logging, event_level),  # Send errors as events
            )

            def before_send(event, hint):
                if "exc_info" in hint:
                    exc_type, exc_value, tb = hint["exc_info"]
                    if isinstance(exc_value, ToolTemplatingException):
                        # We set a custom fingerprint that may look like:
                        # ["Error occurred while {action_str.lower()} for tool '{tool.id}'",
                        #  "1.0",
                        #  "cannot find 'file_name' while searching for 'species_chromosomes.file_name'"]
                        # If we don't do this issues are never properly grouped since by default the calling stack is inspected,
                        # and that is always unique in cheetah as it is dynamically generated.
                        event["fingerprint"] = [str(exc_value), str(exc_value.tool_version), str(exc_value.__cause__)]
                        event.setdefault("tags", {}).update(
                            {
                                "tool_is_latest": exc_value.is_latest,
                                "tool_id": str(exc_value.tool_id),
                                "tool_version": exc_value.tool_version,
                            }
                        )
                return event

            self.sentry_client = sentry_sdk.init(
                self.config.sentry_dsn,
                release=f"{self.config.version_major}.{self.config.version_minor}",
                integrations=[sentry_logging],
                traces_sample_rate=self.config.sentry_traces_sample_rate,
                ca_certs=self.config.sentry_ca_certs,
                before_send=before_send,
            )


class MinimalGalaxyApplication(BasicSharedApp, HaltableContainer, SentryClientMixin, HasToolBox):
    """Encapsulates the state of a minimal Galaxy application"""

    model: GalaxyModelMapping
    config: GalaxyAppConfiguration
    tool_cache: ToolCache
    job_config: jobs.JobConfiguration
    toolbox_search: ToolBoxSearch
    container_finder: containers.ContainerFinder
    install_model: ModelMapping
    object_store: BaseObjectStore

    def __init__(self, fsmon=False, **kwargs) -> None:
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
        self.name = "galaxy"
        self.is_webapp = False
        # Read config file and check for errors
        self.config = self._register_singleton(GalaxyAppConfiguration, GalaxyAppConfiguration(**kwargs))
        self.config.check()
        config_file = kwargs.get("global_conf", {}).get("__file__", None)
        if config_file:
            log.debug('Using "galaxy.ini" config file: %s', config_file)
        self._configure_models(check_migrate_databases=self.config.check_migrate_databases, config_file=config_file)
        # Security helper
        self._configure_security()
        self._register_singleton(IdEncodingHelper, self.security)
        self._register_singleton(SharedModelMapping, self.model)
        self._register_singleton(GalaxyModelMapping, self.model)
        self._register_singleton(galaxy_scoped_session, self.model.context)
        self._register_singleton(install_model_scoped_session, self.install_model.context)
        # Load quota management.
        self.quota_agent = self._register_singleton(QuotaAgent, get_quota_agent(self.config, self.model))
        self.vault = self._register_singleton(Vault, VaultFactory.from_app(self))  # type: ignore[type-abstract]
        self._configure_object_store(fsmon=True)
        self._register_singleton(BaseObjectStore, self.object_store)
        galaxy.model.setup_global_object_store_for_models(self.object_store)

    def configure_fluent_log(self):
        if self.config.fluent_log:
            from galaxy.util.custom_logging.fluent_log import FluentTraceLogger

            self.trace_logger: Optional[FluentTraceLogger] = FluentTraceLogger(
                "galaxy", self.config.fluent_host, self.config.fluent_port
            )
        else:
            self.trace_logger = None

    def _configure_genome_builds(self, data_table_name="__dbkeys__", load_old_style=True):
        self.genome_builds = GenomeBuilds(self, data_table_name=data_table_name, load_old_style=load_old_style)

    def wait_for_toolbox_reload(self, old_toolbox):
        timer = ExecutionTimer()
        log.debug("Waiting for toolbox reload")
        # Wait till toolbox reload has been triggered (or more than 60 seconds have passed)
        while timer.elapsed < 60:
            if self.toolbox.has_reloaded(old_toolbox):
                log.debug("Finished waiting for toolbox reload %s", timer)
                break
            time.sleep(0.1)
        else:
            log.warning("Waiting for toolbox reload timed out after 60 seconds")

    def _configure_tool_config_files(self):
        if self.config.shed_tool_config_file not in self.config.tool_configs:
            self.config.tool_configs.append(self.config.shed_tool_config_file)
        # The value of migrated_tools_config is the file reserved for containing only those tools that have been
        # eliminated from the distribution and moved to the tool shed. If migration checking is disabled, only add it if
        # it exists (since this may be an existing deployment where migrations were previously run).
        if (
            os.path.exists(self.config.migrated_tools_config)
            and self.config.migrated_tools_config not in self.config.tool_configs
        ):
            self.config.tool_configs.append(self.config.migrated_tools_config)

    def _configure_toolbox(self):
        self.citations_manager = CitationsManager(self)
        self.biotools_metadata_source = get_galaxy_biotools_metadata_source(self.config)

        self.dynamic_tool_manager = DynamicToolManager(self)
        self._toolbox_lock = threading.RLock()
        self._toolbox = tools.ToolBox(self.config.tool_configs, self.config.tool_path, self)
        galaxy_root_dir = os.path.abspath(self.config.root)
        file_path = os.path.abspath(self.config.file_path)
        app_info = AppInfo(
            galaxy_root_dir=galaxy_root_dir,
            default_file_path=file_path,
            tool_data_path=self.config.tool_data_path,
            galaxy_data_manager_data_path=self.config.galaxy_data_manager_data_path,
            shed_tool_data_path=self.config.shed_tool_data_path,
            outputs_to_working_directory=self.config.outputs_to_working_directory,
            container_image_cache_path=self.config.container_image_cache_path,
            library_import_dir=self.config.library_import_dir,
            enable_mulled_containers=self.config.enable_mulled_containers,
            container_resolvers_config_file=self.config.container_resolvers_config_file,
            container_resolvers_config_dict=self.config.container_resolvers,
            involucro_path=self.config.involucro_path,
            involucro_auto_init=self.config.involucro_auto_init,
            mulled_channels=self.config.mulled_channels,
        )
        mulled_resolution_cache = None
        if self.config.mulled_resolution_cache_type:
            cache_opts = {
                "cache.type": self.config.mulled_resolution_cache_type,
                "cache.data_dir": self.config.mulled_resolution_cache_data_dir,
                "cache.lock_dir": self.config.mulled_resolution_cache_lock_dir,
                "cache.expire": self.config.mulled_resolution_cache_expire,
                "cache.url": self.config.mulled_resolution_cache_url,
                "cache.table_name": self.config.mulled_resolution_cache_table_name,
                "cache.schema_name": self.config.mulled_resolution_cache_schema_name,
            }
            mulled_resolution_cache = CacheManager(**parse_cache_config_options(cache_opts)).get_cache(
                "mulled_resolution"
            )
        self.container_finder = containers.ContainerFinder(app_info, mulled_resolution_cache=mulled_resolution_cache)
        self._set_enabled_container_types()
        index_help = getattr(self.config, "index_tool_help", True)
        self.toolbox_search = self._register_singleton(
            ToolBoxSearch,
            ToolBoxSearch(self.toolbox, index_dir=self.config.tool_search_index_dir, index_help=index_help),
        )

    @property
    def toolbox(self) -> tools.ToolBox:
        return self._toolbox

    def reindex_tool_search(self) -> None:
        # Call this when tools are added or removed.
        self.toolbox_search.build_index(tool_cache=self.tool_cache, toolbox=self.toolbox)
        self.tool_cache.reset_status()

    def _set_enabled_container_types(self):
        container_types_to_destinations = collections.defaultdict(list)
        for destinations in self.job_config.destinations.values():
            for destination in destinations:
                for enabled_container_type in self.container_finder._enabled_container_types(destination.params):
                    container_types_to_destinations[enabled_container_type].append(destination)
        self.toolbox.dependency_manager.set_enabled_container_types(container_types_to_destinations)
        self.toolbox.dependency_manager.resolver_classes.update(
            self.container_finder.default_container_registry.resolver_classes
        )
        self.toolbox.dependency_manager.dependency_resolvers.extend(
            self.container_finder.default_container_registry.container_resolvers
        )

    def _configure_tool_data_tables(self, from_shed_config):
        # Initialize tool data tables using the config defined by self.config.tool_data_table_config_path.
        self.tool_data_tables: BaseToolDataTableManager = ToolDataTableManager(
            tool_data_path=self.config.tool_data_path,
            config_filename=self.config.tool_data_table_config_path,
            other_config_dict=self.config,
        )
        # Load additional entries defined by self.config.shed_tool_data_table_config into tool data tables.
        try:
            self.tool_data_tables.load_from_config_file(
                config_filename=self.config.shed_tool_data_table_config,
                tool_data_path=self.tool_data_tables.tool_data_path,
                from_shed_config=from_shed_config,
            )
        except OSError as exc:
            # Missing shed_tool_data_table_config is okay if it's the default
            if exc.errno != errno.ENOENT or self.config.is_set("shed_tool_data_table_config"):
                raise

    def _configure_datatypes_registry(self, use_display_applications=True, use_converters=True):
        # Create an empty datatypes registry.
        self.datatypes_registry = Registry(self.config)
        # Load the data types in the Galaxy distribution, which are defined in self.config.datatypes_config.
        datatypes_configs = self.config.datatypes_config
        for datatypes_config in listify(datatypes_configs):
            # Setting override=False would make earlier files would take
            # precedence - but then they wouldn't override tool shed
            # datatypes.
            self.datatypes_registry.load_datatypes(
                self.config.root,
                datatypes_config,
                override=True,
                use_display_applications=use_display_applications,
                use_converters=use_converters,
            )

    def _configure_object_store(self, **kwds):
        app_config = UserObjectStoresAppConfig(
            jobs_directory=self.config.jobs_directory,
            new_file_path=self.config.new_file_path,
            umask=self.config.umask,
            gid=self.config.gid,
            object_store_cache_size=self.config.object_store_cache_size,
            object_store_cache_path=self.config.object_store_cache_path,
            user_config_templates_use_saved_configuration=self.config.user_config_templates_use_saved_configuration,
        )
        self._register_singleton(UserObjectStoresAppConfig, app_config)
        vault_configured = is_vault_configured(self.vault)
        templates = ConfiguredObjectStoreTemplates.from_app_config(self.config, vault_configured=vault_configured)
        self.object_store_templates = self._register_singleton(ConfiguredObjectStoreTemplates, templates)
        user_object_store_resolver = self._register_abstract_singleton(
            UserObjectStoreResolver, UserObjectStoreResolverImpl  # type: ignore[type-abstract]
        )  # Ignored because of https://github.com/python/mypy/issues/4717
        kwds["user_object_store_resolver"] = user_object_store_resolver
        self.object_store = build_object_store_from_config(self.config, **kwds)

    def _configure_security(self):
        self.security = IdEncodingHelper(id_secret=self.config.id_secret)
        Security.security = self.security

    def _configure_engines(self, db_url, install_db_url, combined_install_database):
        trace_logger = getattr(self, "trace_logger", None)
        engine = build_engine(
            db_url,
            self.config.database_engine_options,
            self.config.database_query_profiling_proxy,
            trace_logger,
            self.config.slow_query_log_threshold,
            self.config.thread_local_log,
            self.config.database_log_query_counts,
        )
        install_engine = None
        if not combined_install_database:
            install_engine = build_engine(install_db_url, self.config.install_database_engine_options)
        return engine, install_engine

    def _configure_models(self, check_migrate_databases=False, config_file=None):
        """Preconditions: object_store must be set on self."""
        # TODO this block doesn't seem to belong in this method
        if getattr(self.config, "max_metadata_value_size", None):
            custom_types.MAX_METADATA_VALUE_SIZE = self.config.max_metadata_value_size

        db_url = self.config.database_connection
        install_db_url = self.config.install_database_connection
        combined_install_database = is_one_database(db_url, install_db_url)
        engine, install_engine = self._configure_engines(db_url, install_db_url, combined_install_database)

        if self.config.database_wait:
            self._wait_for_database(db_url)

        if check_migrate_databases:
            self._verify_databases(engine, install_engine, combined_install_database)

        self.model = mapping.configure_model_mapping(
            self.config.file_path,
            self.config.use_pbkdf2,
            engine,
            combined_install_database,
            self.config.thread_local_log,
        )

        if combined_install_database:
            log.info("Install database targeting Galaxy's database configuration.")  # TODO this message is ambiguous
            self.install_model = self.model
        else:
            self.install_model = install_mapping.configure_model_mapping(install_engine)
            log.info(f"Install database using its own connection {install_db_url}")

    def _verify_databases(self, engine, install_engine, combined_install_database):
        install_template, install_encoding = None, None
        if not combined_install_database:  # Otherwise these options are not used.
            install_template = getattr(self.config, "install_database_template", None)
            install_encoding = getattr(self.config, "install_database_encoding", None)

        verify_databases(
            engine,
            self.config.database_template,
            self.config.database_encoding,
            install_engine,
            install_template,
            install_encoding,
            self.config.database_auto_migrate,
        )

    def _configure_signal_handlers(self, handlers):
        for sig, handler in handlers.items():
            signal.signal(sig, handler)

    def _wait_for_database(self, url):
        attempts = self.config.database_wait_attempts
        pause = self.config.database_wait_sleep
        for i in range(1, attempts):
            try:
                database_exists(url)
                break
            except Exception:
                log.info("Waiting for database: attempt %d of %d", i, attempts)
                time.sleep(pause)

    @property
    def tool_dependency_dir(self) -> Optional[str]:
        return self.toolbox.dependency_manager.default_base_path

    def _shutdown_object_store(self):
        self.object_store.shutdown()

    def _shutdown_model(self):
        self.model.engine.dispose()


class GalaxyManagerApplication(MinimalManagerApp, MinimalGalaxyApplication, InstallationTarget[tools.ToolBox]):
    """Extends the MinimalGalaxyApplication with most managers that are not tied to a web or job handling context."""

    model: GalaxyModelMapping

    def __init__(self, configure_logging=True, use_converters=True, use_display_applications=True, **kwargs):
        super().__init__(**kwargs)
        self._register_singleton(MinimalManagerApp, self)  # type: ignore[type-abstract]
        self.execution_timer_factory = self._register_singleton(
            ExecutionTimerFactory, ExecutionTimerFactory(self.config)
        )
        self.configure_fluent_log()
        self.application_stack = self._register_singleton(ApplicationStack, application_stack_instance(app=self))
        if configure_logging:
            config.configure_logging(self.config, self.application_stack.facts)
        # Carbon emissions configuration
        carbon_intensity_entry = get_carbon_intensity_entry(self.config.geographical_server_location_code)
        self.carbon_intensity = carbon_intensity_entry["carbon_intensity"]
        self.geographical_server_location_name = carbon_intensity_entry["location_name"]
        # Initialize job metrics manager, needs to be in place before
        # config so per-destination modifications can be made.
        self.job_metrics = self._register_singleton(
            JobMetrics, JobMetrics(self.config.job_metrics_config_file, self.config.job_metrics, app=self)
        )
        # Initialize the job management configuration
        self.job_config = self._register_singleton(jobs.JobConfiguration)

        # Setup infrastructure for short term storage manager.
        short_term_storage_config_kwds: Dict[str, Any] = {}
        short_term_storage_config_kwds["short_term_storage_directory"] = self.config.short_term_storage_dir
        short_term_storage_default_duration = self.config.short_term_storage_default_duration
        short_term_storage_maximum_duration = self.config.short_term_storage_maximum_duration
        if short_term_storage_default_duration is not None:
            short_term_storage_config_kwds["default_storage_duration"] = short_term_storage_default_duration
        if short_term_storage_maximum_duration:
            short_term_storage_config_kwds["maximum_storage_duration"] = short_term_storage_maximum_duration

        short_term_storage_config = ShortTermStorageConfiguration(**short_term_storage_config_kwds)
        short_term_storage_manager = ShortTermStorageManager(config=short_term_storage_config)
        self._register_singleton(ShortTermStorageAllocator, short_term_storage_manager)  # type: ignore[type-abstract]
        self._register_singleton(ShortTermStorageMonitor, short_term_storage_manager)  # type: ignore[type-abstract]

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
        self.job_manager = self._register_singleton(JobManager)
        self.notification_manager = self._register_singleton(NotificationManager)

        self.task_manager = self._register_abstract_singleton(
            AsyncTasksManager, CeleryAsyncTasksManager  # type: ignore[type-abstract]  # https://github.com/python/mypy/issues/4717
        )

        # ConfiguredFileSources
        vault_configured = is_vault_configured(self.vault)
        templates = ConfiguredFileSourceTemplates.from_app_config(self.config, vault_configured=vault_configured)
        file_sources_config: FileSourcePluginsConfig = FileSourcePluginsConfig.from_app_config(self.config)
        self._register_singleton(FileSourcePluginsConfig, file_sources_config)
        file_source_plugin_loader = FileSourcePluginLoader()
        self._register_singleton(FileSourcePluginLoader, file_source_plugin_loader)
        self.file_source_templates = self._register_singleton(ConfiguredFileSourceTemplates, templates)
        self._register_singleton(
            UserDefinedFileSourcesConfig, UserDefinedFileSourcesConfig.from_app_config(self.config)
        )
        user_defined_file_sources = self._register_abstract_singleton(
            UserDefinedFileSources, UserDefinedFileSourcesImpl  # type: ignore[type-abstract]  # https://github.com/python/mypy/issues/4717
        )
        configured_file_source_conf: ConfiguredFileSourcesConf = ConfiguredFileSourcesConf.from_app_config(self.config)
        file_sources = ConfiguredFileSources(
            file_sources_config,
            configured_file_source_conf,
            load_stock_plugins=True,
            plugin_loader=file_source_plugin_loader,
            user_defined_file_sources=user_defined_file_sources,
        )
        self.file_sources = self._register_singleton(ConfiguredFileSources, file_sources)
        self._register_singleton(FileSourceInstancesManager)

        # Load security policy.
        self.security_agent = self.model.security_agent
        self.host_security_agent = galaxy.model.security.HostAgent(
            self.security_agent.sa_session, permitted_actions=self.security_agent.permitted_actions
        )

        # We need the datatype registry for running certain tasks that modify HDAs, and to build the registry we need
        # to setup the installed repositories ... this is not ideal
        self._configure_tool_config_files()
        self.installed_repository_manager = self._register_singleton(
            InstalledRepositoryManager, InstalledRepositoryManager(self)
        )
        self.dynamic_tool_manager = self._register_singleton(DynamicToolManager)
        self.trs_proxy = self._register_singleton(TrsProxy, TrsProxy(self.config))
        self._configure_datatypes_registry(
            use_converters=use_converters,
            use_display_applications=use_display_applications,
        )
        self._register_singleton(Registry, self.datatypes_registry)
        galaxy.model.set_datatypes_registry(self.datatypes_registry)
        self.configure_sentry_client()

        self._configure_tool_shed_registry()
        self._register_singleton(tool_shed_registry.Registry, self.tool_shed_registry)
        self._register_celery_galaxy_task_components()

    def _register_celery_galaxy_task_components(self):
        """
        Register subtype class instance to support implementation of a user rate limit for execution of celery tasks.
        The default supertype class does not enforce a user rate limit. This is the case if the celery_user_rate_limit
        config param is the default value.
        """
        task_before_start: GalaxyTaskBeforeStart
        if self.config.celery_user_rate_limit:
            if is_postgres(self.config.database_connection):  # type: ignore[arg-type]
                task_before_start = GalaxyTaskBeforeStartUserRateLimitPostgres(
                    self.config.celery_user_rate_limit, self.model.session
                )
            else:
                task_before_start = GalaxyTaskBeforeStartUserRateLimitStandard(
                    self.config.celery_user_rate_limit, self.model.session
                )
        else:
            task_before_start = GalaxyTaskBeforeStart()
        self._register_singleton(GalaxyTaskBeforeStart, task_before_start)

    def _configure_tool_shed_registry(self) -> None:
        # Set up the tool sheds registry
        if os.path.isfile(self.config.tool_sheds_config_file):
            self.tool_shed_registry = tool_shed_registry.Registry(self.config.tool_sheds_config_file)
        else:
            self.tool_shed_registry = tool_shed_registry.Registry()

    @property
    def is_job_handler(self) -> bool:
        return (
            self.config.track_jobs_in_database and self.job_config.is_handler
        ) or not self.config.track_jobs_in_database


class UniverseApplication(StructuredApp, GalaxyManagerApplication):
    """Encapsulates the state of a Universe application"""

    model: GalaxyModelMapping

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
            ("database connection", self._shutdown_model),
            ("application stack", self._shutdown_application_stack),
        ]
        self._register_singleton(StructuredApp, self)  # type: ignore[type-abstract]
        if kwargs.get("is_webapp"):
            self.is_webapp = kwargs["is_webapp"]
        # A lot of postfork initialization depends on the server name, ensure it is set immediately after forking before other postfork functions
        self.application_stack.register_postfork_function(self.application_stack.set_postfork_server_name, self)
        self.config.reload_sanitize_allowlist(explicit="sanitize_allowlist_file" in kwargs)
        self.amqp_internal_connection_obj = galaxy.queues.connection_from_config(self.config)
        # queue_worker *can* be initialized with a queue, but here we don't
        # want to and we'll allow postfork to bind and start it.
        self.queue_worker = self._register_singleton(GalaxyQueueWorker, GalaxyQueueWorker(self))

        self.dependency_resolvers_view = self._register_singleton(
            DependencyResolversView, DependencyResolversView(self)
        )
        self.test_data_resolver = self._register_singleton(
            TestDataResolver, TestDataResolver(file_dirs=self.config.tool_test_data_directories)
        )
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
        self.error_reports = self._register_singleton(
            ErrorReports, ErrorReports(self.config.error_report_file, app=self)
        )

        # Setup a Tool Cache
        self.tool_cache = self._register_singleton(ToolCache)
        self.tool_shed_repository_cache = self._register_singleton(ToolShedRepositoryCache)
        # Watch various config files for immediate reload
        self.watchers = self._register_singleton(ConfigWatchers)
        self._configure_toolbox()
        # Load Data Manager
        self.data_managers = self._register_singleton(DataManagers)
        # Load the update repository manager.
        self.update_repository_manager = self._register_singleton(
            UpdateRepositoryManager, UpdateRepositoryManager(self)
        )
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
        self.visualizations_registry = self._register_singleton(
            VisualizationsRegistry,
            VisualizationsRegistry(
                self,
                directories_setting=self.config.visualization_plugins_directory,
                template_cache_dir=self.config.template_cache_path,
            ),
        )
        # Tours registry
        tour_registry = build_tours_registry(self.config.tour_config_dir)
        self.tour_registry = tour_registry
        self[ToursRegistry] = tour_registry  # type: ignore[type-abstract]
        # Webhooks registry
        self.webhooks_registry = self._register_singleton(WebhooksRegistry, WebhooksRegistry(self.config.webhooks_dir))
        # Heartbeat for thread profiling
        self.heartbeat = None
        self.auth_manager = self._register_singleton(auth.AuthManager, auth.AuthManager(self.config))
        # Start the heartbeat process if configured and available
        if self.config.use_heartbeat:
            self.heartbeat = heartbeat.Heartbeat(
                self.config, period=self.config.heartbeat_interval, fname=self.config.heartbeat_log
            )
            self.heartbeat.daemon = True
            self.application_stack.register_postfork_function(self.heartbeat.start)

        self.authnz_manager = None
        if self.config.enable_oidc:
            from galaxy.authnz import managers

            self.authnz_manager = managers.AuthnzManager(
                self, self.config.oidc_config_file, self.config.oidc_backends_config_file
            )

            # If there is only a single external authentication provider in use
            # TODO: Future work will expand on this and provide an interface for
            # multiple auth providers allowing explicit authenticated association.
            self.config.fixed_delegated_auth = (
                len(list(self.config.oidc)) == 1 and len(list(self.auth_manager.authenticators)) == 0
            )

        if not self.config.enable_celery_tasks and self.config.history_audit_table_prune_interval > 0:
            self.prune_history_audit_task = IntervalTask(
                func=lambda: galaxy.model.HistoryAudit.prune(self.model.session),
                name="HistoryAuditTablePruneTask",
                interval=self.config.history_audit_table_prune_interval,
                immediate_start=False,
                time_execution=True,
            )
            self.application_stack.register_postfork_function(self.prune_history_audit_task.start)
            self.haltables.append(("HistoryAuditTablePruneTask", self.prune_history_audit_task.shutdown))
        self.proxy_manager = ProxyManager(self.config)

        # Must be initialized after job_config.
        self.workflow_scheduling_manager = scheduling_manager.WorkflowSchedulingManager(self)

        # We need InteractiveToolManager before the job handler starts
        self.interactivetool_manager = InteractiveToolManager(self)
        # Start the job manager
        self.application_stack.register_postfork_function(self.job_manager.start)
        # Must be initialized after any component that might make use of stack messaging is configured. Alternatively if
        # it becomes more commonly needed we could create a prefork function registration method like we do with
        # postfork functions.
        self.application_stack.init_late_prefork()

        # Configure handling of signals
        handlers = {}
        if self.heartbeat:
            handlers[signal.SIGUSR1] = self.heartbeat.dump_signal_handler
        self._configure_signal_handlers(handlers)

        self.database_heartbeat = DatabaseHeartbeat(application_stack=self.application_stack)
        self.database_heartbeat.add_change_callback(self.watchers.change_state)
        self.application_stack.register_postfork_function(self.database_heartbeat.start)

        # Start web stack message handling
        self.application_stack.register_postfork_function(self.application_stack.start)
        self.application_stack.register_postfork_function(self.queue_worker.bind_and_start)
        # Reload toolbox to pick up changes to toolbox made after master was ready
        self.application_stack.register_postfork_function(
            lambda: reload_toolbox(self, save_integrated_tool_panel=False), post_fork_only=True
        )
        # Delay toolbox index until after startup
        self.application_stack.register_postfork_function(
            lambda: send_local_control_task(self, "rebuild_toolbox_search_index")
        )

        # Inject url_for for components to more easily optionally depend
        # on url_for.
        self.url_for = url_for

        self.server_starttime = server_starttime  # used for cachebusting
        # Limit lifetime of tool shed repository cache to app startup
        self.tool_shed_repository_cache = None
        self.api_spec = None
        self.legacy_mapper = None
        self.application_stack.register_postfork_function(self.object_store.start)
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

    def _shutdown_application_stack(self):
        self.application_stack.shutdown()


class StatsdStructuredExecutionTimer(StructuredExecutionTimer):
    def __init__(self, galaxy_statsd_client, *args, **kwds):
        self.galaxy_statsd_client = galaxy_statsd_client
        super().__init__(*args, **kwds)

    def to_str(self, **kwd):
        self.galaxy_statsd_client.timing(self.timer_id, self.elapsed * 1000.0, kwd)
        return super().to_str(**kwd)


class ExecutionTimerFactory:
    def __init__(self, config):
        if statsd_host := getattr(config, "statsd_host", None):
            from galaxy.web.statsd_client import GalaxyStatsdClient

            self.galaxy_statsd_client: Optional[GalaxyStatsdClient] = GalaxyStatsdClient(
                statsd_host,
                getattr(config, "statsd_port", 8125),
                getattr(config, "statsd_prefix", "galaxy"),
                getattr(config, "statsd_influxdb", False),
                getattr(config, "statsd_mock_calls", False),
            )
        else:
            self.galaxy_statsd_client = None

    def get_timer(self, *args, **kwd):
        if self.galaxy_statsd_client:
            return StatsdStructuredExecutionTimer(self.galaxy_statsd_client, *args, **kwd)
        else:
            return StructuredExecutionTimer(*args, **kwd)
