from galaxy.tools.deps.requirements import ToolRequirements
from galaxy.util import bunch
from .mulled.mulled_build import DEFAULT_CHANNELS


class AppInfo(object):

    def __init__(
        self,
        galaxy_root_dir=None,
        default_file_path=None,
        outputs_to_working_directory=False,
        container_image_cache_path=None,
        library_import_dir=None,
        enable_beta_mulled_containers=False,
        containers_resolvers_config_file=None,
        involucro_path=None,
        involucro_auto_init=True,
        mulled_channels=DEFAULT_CHANNELS,
    ):
        self.galaxy_root_dir = galaxy_root_dir
        self.default_file_path = default_file_path
        # TODO: Vary default value for docker_volumes based on this...
        self.outputs_to_working_directory = outputs_to_working_directory
        self.container_image_cache_path = container_image_cache_path
        self.library_import_dir = library_import_dir
        self.enable_beta_mulled_containers = enable_beta_mulled_containers
        self.containers_resolvers_config_file = containers_resolvers_config_file
        self.involucro_path = involucro_path
        self.involucro_auto_init = involucro_auto_init
        self.mulled_channels = mulled_channels


class ToolInfo(object):
    # TODO: Introduce tool XML syntax to annotate the optional environment
    # variables they can consume (e.g. JVM options, license keys, etc..)
    # and add these to env_path_through

    def __init__(self, container_descriptions=None, requirements=None, requires_galaxy_python_environment=False, env_pass_through=["GALAXY_SLOTS"]):
        if container_descriptions is None:
            container_descriptions = []
        if requirements is None:
            requirements = []
        self.container_descriptions = container_descriptions
        self.requirements = requirements
        self.requires_galaxy_python_environment = requires_galaxy_python_environment
        self.env_pass_through = env_pass_through


class JobInfo(object):

    def __init__(
        self, working_directory, tool_directory, job_directory, tmp_directory, job_directory_type
    ):
        self.working_directory = working_directory
        self.job_directory = job_directory
        # Tool files may be remote staged - so this is unintuitively a property
        # of the job not of the tool.
        self.tool_directory = tool_directory
        self.tmp_directory = tmp_directory
        self.job_directory_type = job_directory_type  # "galaxy" or "pulsar"


class DependenciesDescription(object):
    """ Capture (in a readily serializable way) context related a tool
    dependencies - both the tool's listed requirements and the tool shed
    related context required to resolve dependencies via the
    ToolShedPackageDependencyResolver.

    This is meant to enable remote resolution of dependencies, by the Pulsar or
    other potential remote execution mechanisms.
    """

    def __init__(self, requirements=[], installed_tool_dependencies=[]):
        self.requirements = requirements
        # tool shed installed tool dependencies...
        self.installed_tool_dependencies = installed_tool_dependencies

    def to_dict(self):
        return dict(
            requirements=[r.to_dict() for r in self.requirements],
            installed_tool_dependencies=[DependenciesDescription._toolshed_install_dependency_to_dict(d) for d in self.installed_tool_dependencies]
        )

    @staticmethod
    def from_dict(as_dict):
        if as_dict is None:
            return None

        requirements_dicts = as_dict.get('requirements', [])
        requirements = ToolRequirements.from_list(requirements_dicts)
        installed_tool_dependencies_dicts = as_dict.get('installed_tool_dependencies', [])
        installed_tool_dependencies = map(DependenciesDescription._toolshed_install_dependency_from_dict, installed_tool_dependencies_dicts)
        return DependenciesDescription(
            requirements=requirements,
            installed_tool_dependencies=installed_tool_dependencies
        )

    @staticmethod
    def _toolshed_install_dependency_from_dict(as_dict):
        # Rather than requiring full models in Pulsar, just use simple objects
        # containing only properties and associations used to resolve
        # dependencies for tool execution.
        repository_object = bunch.Bunch(
            name=as_dict['repository_name'],
            owner=as_dict['repository_owner'],
            installed_changeset_revision=as_dict['repository_installed_changeset'],
        )
        dependency_object = bunch.Bunch(
            name=as_dict['dependency_name'],
            version=as_dict['dependency_version'],
            type=as_dict['dependency_type'],
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
