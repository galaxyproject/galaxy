from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from galaxy.tool_util.deps.requirements import (
    ContainerDescription,
    ToolRequirement,
    ToolRequirements,
)
from galaxy.util import bunch
from .mulled.util import DEFAULT_CHANNELS


class AppInfo:
    def __init__(
        self,
        galaxy_root_dir: Optional[str] = None,
        default_file_path: Optional[str] = None,
        tool_data_path: Optional[str] = None,
        shed_tool_data_path: Optional[str] = None,
        outputs_to_working_directory: bool = False,
        container_image_cache_path: Optional[str] = None,
        library_import_dir: Optional[str] = None,
        enable_mulled_containers: bool = False,
        container_resolvers_config_file: Optional[str] = None,
        container_resolvers_config_dict: Optional[Dict[str, Any]] = None,
        involucro_path: Optional[str] = None,
        involucro_auto_init: bool = True,
        mulled_channels: List[str] = DEFAULT_CHANNELS,
    ) -> None:
        self.galaxy_root_dir = galaxy_root_dir
        self.default_file_path = default_file_path
        self.tool_data_path = tool_data_path
        self.shed_tool_data_path = shed_tool_data_path
        # TODO: Vary default value for docker_volumes based on this...
        self.outputs_to_working_directory = outputs_to_working_directory
        self.container_image_cache_path = container_image_cache_path
        self.library_import_dir = library_import_dir
        self.enable_mulled_containers = enable_mulled_containers
        self.container_resolvers_config_file = container_resolvers_config_file
        self.container_resolvers_config_dict = container_resolvers_config_dict
        self.involucro_path = involucro_path
        self.involucro_auto_init = involucro_auto_init
        self.mulled_channels = mulled_channels


class ToolInfo:
    # TODO: Introduce tool XML syntax to annotate the optional environment
    # variables they can consume (e.g. JVM options, license keys, etc..)
    # and add these to env_path_through

    def __init__(
        self,
        container_descriptions: Optional[List["ContainerDescription"]] = None,
        requirements: Optional[Union["ToolRequirements", List["ToolRequirement"]]] = None,
        requires_galaxy_python_environment: bool = False,
        env_pass_through=None,
        guest_ports=None,
        tool_id: Optional[str] = None,
        tool_version: Optional[str] = None,
        profile: float = -1,
    ):
        if env_pass_through is None:
            env_pass_through = ["GALAXY_SLOTS", "GALAXY_MEMORY_MB", "GALAXY_MEMORY_MB_PER_SLOT"]
        if container_descriptions is None:
            container_descriptions = []
        if requirements is None:
            requirements = []
        self.container_descriptions = container_descriptions
        self.requirements = requirements
        self.requires_galaxy_python_environment = requires_galaxy_python_environment
        self.env_pass_through = env_pass_through
        self.guest_ports = guest_ports
        self.tool_id = tool_id
        self.tool_version = tool_version
        self.profile = profile


class JobInfo:
    def __init__(
        self,
        working_directory,
        tool_directory,
        job_directory,
        tmp_directory,
        home_directory,
        job_directory_type,
    ):
        self.working_directory = working_directory
        # Tool files may be remote staged - so this is unintuitively a property
        # of the job not of the tool.
        self.tool_directory = tool_directory
        self.job_directory = job_directory
        self.tmp_directory = tmp_directory
        self.home_directory = home_directory
        self.job_directory_type = job_directory_type  # "galaxy" or "pulsar"


class DependenciesDescription:
    """Capture (in a readily serializable way) context related a tool
    dependencies - both the tool's listed requirements and the tool shed
    related context required to resolve dependencies via the
    ToolShedPackageDependencyResolver.

    This is meant to enable remote resolution of dependencies, by the Pulsar or
    other potential remote execution mechanisms.
    """

    def __init__(self, requirements=None, installed_tool_dependencies=None):
        requirements = requirements or ToolRequirements()
        if installed_tool_dependencies is None:
            installed_tool_dependencies = []
        self.requirements = requirements
        # tool shed installed tool dependencies...
        self.installed_tool_dependencies = installed_tool_dependencies

    def to_dict(self):
        return dict(
            requirements=[r.to_dict() for r in self.requirements],
            installed_tool_dependencies=[
                self._toolshed_install_dependency_to_dict(d) for d in self.installed_tool_dependencies
            ],
        )

    @classmethod
    def from_dict(cls, as_dict):
        if as_dict is None:
            return None

        requirements_dicts = as_dict.get("requirements", [])
        requirements = ToolRequirements.from_list(requirements_dicts)
        installed_tool_dependencies_dicts = as_dict.get("installed_tool_dependencies", [])
        installed_tool_dependencies = list(
            map(cls._toolshed_install_dependency_from_dict, installed_tool_dependencies_dicts)
        )
        return cls(requirements=requirements, installed_tool_dependencies=installed_tool_dependencies)

    @staticmethod
    def _toolshed_install_dependency_from_dict(as_dict):
        # Rather than requiring full models in Pulsar, just use simple objects
        # containing only properties and associations used to resolve
        # dependencies for tool execution.
        repository_object = bunch.Bunch(
            name=as_dict["repository_name"],
            owner=as_dict["repository_owner"],
            installed_changeset_revision=as_dict["repository_installed_changeset"],
        )
        dependency_object = bunch.Bunch(
            name=as_dict["dependency_name"],
            version=as_dict["dependency_version"],
            type=as_dict["dependency_type"],
            tool_shed_repository=repository_object,
        )
        return dependency_object

    @staticmethod
    def _toolshed_install_dependency_to_dict(tool_dependency):
        tool_shed_repository = tool_dependency.tool_shed_repository
        return dict(
            dependency_name=tool_dependency.name,
            dependency_version=tool_dependency.version,
            dependency_type=tool_dependency.type,
            repository_name=tool_shed_repository.name,
            repository_owner=tool_shed_repository.owner,
            repository_installed_changeset=tool_shed_repository.installed_changeset_revision,
        )
