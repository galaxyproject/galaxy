from galaxy.tools.deps.requirements import ToolRequirements
from galaxy.util import bunch


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
