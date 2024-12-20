"""Typed description of Galaxy's app object."""

import abc
import threading
from typing import (
    Any,
    Optional,
    TYPE_CHECKING,
)

from kombu import Connection
from typing_extensions import Protocol

from galaxy.auth import AuthManager
from galaxy.datatypes.registry import Registry
from galaxy.di import Container
from galaxy.files import ConfiguredFileSources
from galaxy.job_metrics import JobMetrics
from galaxy.managers.dbkeys import GenomeBuilds
from galaxy.model.base import (
    ModelMapping,
    SharedModelMapping,
)
from galaxy.model.mapping import GalaxyModelMapping
from galaxy.model.security import (
    GalaxyRBACAgent,
    HostAgent,
)
from galaxy.model.tags import GalaxyTagHandler
from galaxy.objectstore import BaseObjectStore
from galaxy.quota import QuotaAgent
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.security.vault import Vault
from galaxy.tool_shed.cache import ToolShedRepositoryCache
from galaxy.tool_util.deps.containers import ContainerFinder
from galaxy.tool_util.deps.views import DependencyResolversView
from galaxy.tool_util.verify import test_data
from galaxy.util.tool_shed.tool_shed_registry import Registry as ToolShedRegistry
from galaxy.web_stack import ApplicationStack
from galaxy.webhooks import WebhooksRegistry
from galaxy.workflow.trs_proxy import TrsProxy

if TYPE_CHECKING:
    from galaxy.config_watchers import ConfigWatchers
    from galaxy.jobs import JobConfiguration
    from galaxy.managers.collections import DatasetCollectionManager
    from galaxy.managers.folders import FolderManager
    from galaxy.managers.hdas import HDAManager
    from galaxy.managers.histories import HistoryManager
    from galaxy.managers.tools import DynamicToolManager
    from galaxy.managers.workflows import (
        WorkflowContentsManager,
        WorkflowsManager,
    )
    from galaxy.tool_shed.galaxy_install.client import DataManagersInterface
    from galaxy.tool_shed.galaxy_install.installed_repository_manager import InstalledRepositoryManager
    from galaxy.tool_util.data import ToolDataTableManager
    from galaxy.tools import ToolBox
    from galaxy.tools.cache import ToolCache
    from galaxy.tools.error_reports import ErrorReports
    from galaxy.visualization.genomes import Genomes


class BasicSharedApp(Container):
    """Stripped down version of the ``app`` shared between Galaxy and ToolShed.

    Code that is shared between Galaxy and the Tool Shed should be annotated as
    using BasicSharedApp instead of StructuredApp below.
    """

    name: str
    config: Any  # 'galaxy.config.BaseAppConfiguration'
    datatypes_registry: Registry
    application_stack: ApplicationStack
    model: SharedModelMapping
    security: IdEncodingHelper
    auth_manager: AuthManager
    security_agent: Any
    quota_agent: QuotaAgent
    tool_data_tables: "ToolDataTableManager"

    @property
    def toolbox(self) -> "ToolBox":
        raise NotImplementedError()


class MinimalToolApp(Protocol):
    is_webapp: bool
    name: str
    # Leave config as Any: in a full Galaxy app this is a GalaxyAppConfiguration object, but this is mostly dynamically
    # generated, and here we want to also allow other kinds of configuration objects (e.g. a Bunch).
    config: Any
    datatypes_registry: Registry
    object_store: BaseObjectStore
    tool_data_tables: "ToolDataTableManager"
    file_sources: ConfiguredFileSources
    security: IdEncodingHelper


class MinimalApp(BasicSharedApp):
    is_webapp: bool  # is_webapp will be set to true when building WSGI app
    tag_handler: GalaxyTagHandler
    model: GalaxyModelMapping
    install_model: ModelMapping
    security_agent: GalaxyRBACAgent
    host_security_agent: HostAgent
    server_starttime: int


class MinimalManagerApp(MinimalApp):
    # Minimal App that is sufficient to run Celery tasks
    carbon_intensity: float
    file_sources: ConfiguredFileSources
    genome_builds: GenomeBuilds
    geographical_server_location_name: str
    dataset_collection_manager: "DatasetCollectionManager"
    history_manager: "HistoryManager"
    hda_manager: "HDAManager"
    workflow_manager: "WorkflowsManager"
    workflow_contents_manager: "WorkflowContentsManager"
    library_folder_manager: "FolderManager"
    library_manager: Any  # 'galaxy.managers.libraries.LibraryManager'
    role_manager: Any  # 'galaxy.managers.roles.RoleManager'
    user_manager: Any
    job_config: "JobConfiguration"
    job_manager: Any  # galaxy.jobs.manager.JobManager
    job_metrics: JobMetrics
    dynamic_tool_manager: "DynamicToolManager"
    genomes: "Genomes"
    error_reports: "ErrorReports"
    notification_manager: Any  # 'galaxy.managers.notification.NotificationManager'
    object_store: BaseObjectStore
    tool_shed_registry: ToolShedRegistry

    @property
    @abc.abstractmethod
    def is_job_handler(self) -> bool: ...

    def wait_for_toolbox_reload(self, old_toolbox: "ToolBox") -> None: ...


class StructuredApp(MinimalManagerApp):
    """Interface defining typed description of the Galaxy UniverseApplication.

    Ideally nothing that depends on StructuredApp should require
    StructuredApp so we can have a clean import dag. This will
    require setting up a lot more distinction between interfaces
    and implementations in Galaxy though. In the meantime, for
    imports that would bring in StructuredApp if properly type
    (cyclical imports), we're just setting the class attributes to
    Any.
    """

    amqp_internal_connection_obj: Optional[Connection]
    data_managers: "DataManagersInterface"
    dependency_resolvers_view: DependencyResolversView
    installed_repository_manager: "InstalledRepositoryManager"
    container_finder: ContainerFinder
    tool_dependency_dir: Optional[str]
    test_data_resolver: test_data.TestDataResolver
    trs_proxy: TrsProxy
    vault: Vault
    webhooks_registry: WebhooksRegistry
    queue_worker: Any  # 'galaxy.queue_worker.GalaxyQueueWorker'
    data_provider_registry: Any  # 'galaxy.visualization.data_providers.registry.DataProviderRegistry'
    tool_cache: "ToolCache"
    tool_shed_repository_cache: Optional[ToolShedRepositoryCache]
    watchers: "ConfigWatchers"
    workflow_scheduling_manager: Any  # 'galaxy.workflow.scheduling_manager.WorkflowSchedulingManager'
    interactivetool_manager: Any
    api_keys_manager: Any  # 'galaxy.managers.api_keys.ApiKeyManager'
    visualizations_registry: Any  # 'galaxy.visualization.plugins.registry.VisualizationsRegistry'
    _toolbox_lock: threading.RLock
