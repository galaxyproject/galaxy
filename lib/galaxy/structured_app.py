"""Typed description of Galaxy's app object."""
from typing import Any, Optional

from kombu import Connection

from galaxy.auth import AuthManager
from galaxy.files import ConfiguredFileSources
from galaxy.job_metrics import JobMetrics
from galaxy.model.base import ModelMapping
from galaxy.model.mapping import GalaxyModelMapping
from galaxy.model.security import GalaxyRBACAgent
from galaxy.model.security import HostAgent
from galaxy.model.tags import GalaxyTagHandler
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.tool_util.deps.views import DependencyResolversView
from galaxy.tool_util.verify import test_data
from galaxy.util.dbkeys import GenomeBuilds
from galaxy.web_stack import ApplicationStack
from galaxy.webhooks import WebhooksRegistry
from galaxy.workflow.trs_proxy import TrsProxy


class StructuredApp:
    """Interface defining typed description of the Galaxy UniverseApplication.

    Ideally nothing that depends on StructuredApp should require
    StructuredApp so we can have a clean import dag. This will
    require setting up a lot more distinction between interfaces
    and implementations in Galaxy though. In the meantime, for
    imports that would bring in StructuredApp if properly type
    (cyclical imports), we're just setting the class attributes to
    Any.
    """
    name: str
    is_webapp: bool  # is_webapp will be set to true when building WSGI app
    new_installation: bool
    config: Any
    tag_handler: GalaxyTagHandler
    application_stack: ApplicationStack
    amqp_internal_connection_obj: Optional[Connection]
    dependency_resolvers_view: DependencyResolversView
    test_data_resolver: test_data.TestDataResolver
    file_sources: ConfiguredFileSources
    genome_builds: GenomeBuilds
    job_metrics: JobMetrics
    model: GalaxyModelMapping
    install_model: ModelMapping
    security: IdEncodingHelper
    security_agent: GalaxyRBACAgent
    host_security_agent: HostAgent
    auth_manager: AuthManager
    trs_proxy: TrsProxy
    webhooks_registry: WebhooksRegistry

    queue_worker: Any  # 'galaxy.queue_worker.GalaxyQueueWorker'
    dataset_collections_service: Any  # 'galaxy.managers.collections.DatasetCollectionManager'
    history_manager: Any  # 'galaxy.managers.histories.HistoryManager'
    hda_manager: Any  # 'galaxy.managers.hdas.HDAManager'
    workflow_manager: Any  # 'galaxy.managers.workflows.WorkflowsManager'
    workflow_contents_manager: Any  # 'galaxy.managers.workflows.WorkflowContentsManager'
    library_folder_manager: Any  # 'galaxy.managers.folders.FolderManager'
    library_manager: Any  # 'galaxy.managers.libraries.LibraryManager'
    role_manager: Any  # 'galaxy.managers.roles.RoleManager'
    dynamic_tool_manager: Any  # 'galaxy.managers.tools.DynamicToolManager'
    data_provider_registry: Any  # 'galaxy.visualization.data_providers.registry.DataProviderRegistry'
    tool_data_tables: Any  # 'galaxy.tools.data.ToolDataTableManager'
    genomes: Any  # 'galaxy.visualization.genomes.Genomes'
    error_reports: Any  # 'galaxy.tools.error_reports.ErrorReports'
    job_config: Any  # 'galaxy.jobs.JobConfiguration'
    tool_cache: Any  # 'galaxy.tools.cache.ToolCache'
    tool_shed_repository_cache: Any  # 'galaxy.tools.cache.ToolShedRepositoryCache'
    watchers: Any  # 'galaxy.config_watchers.ConfigWatchers'
    installed_repository_manager: Any  # 'galaxy.tool_shed.galaxy_install.installed_repository_manager.InstalledRepositoryManager'
    workflow_scheduling_manager: Any  # 'galaxy.workflow.scheduling_manager.WorkflowSchedulingManager'
    interactivetool_manager: Any
    user_manager: Any
    api_keys_manager: Any
    toolbox: Any
