from os.path import (
    abspath,
    exists,
    join,
)

from . import NullDependency
from .galaxy_packages import (
    BaseGalaxyPackageDependencyResolver,
    ToolShedDependency,
)
from .resolver_mixins import UsesInstalledRepositoriesMixin


class ToolShedPackageDependencyResolver(BaseGalaxyPackageDependencyResolver, UsesInstalledRepositoriesMixin):
    resolver_type = "tool_shed_packages"
    # Resolution of these dependencies depends on more than just the requirement
    # tag, it depends on the tool installation context - therefore these are
    # non-simple.
    dependency_type = ToolShedDependency
    resolves_simple_dependencies = False

    def __init__(self, dependency_manager, **kwds):
        super().__init__(dependency_manager, **kwds)

    def _find_dep_versioned(self, name, version, type="package", **kwds):
        installed_tool_dependency = self._get_installed_dependency(name, type, version=version, **kwds)
        if installed_tool_dependency:
            path = self._get_package_installed_dependency_path(installed_tool_dependency, name, version)
            return self._galaxy_package_dep(path, version, name, type, True)
        else:
            return NullDependency(version=version, name=name)

    def _find_dep_default(self, name, type="package", **kwds):
        if type == "set_environment" and kwds.get("installed_tool_dependencies", None):
            installed_tool_dependency = self._get_installed_dependency(name, type, version=None, **kwds)
            if installed_tool_dependency:
                dependency = self._get_set_environment_installed_dependency_script_path(installed_tool_dependency, name)
                is_galaxy_dep = isinstance(dependency, ToolShedDependency)
                has_script_dep = is_galaxy_dep and dependency.script and dependency.path
                if has_script_dep:
                    # Environment settings do not use versions.
                    return ToolShedDependency(
                        dependency.script,
                        dependency.path,
                        name,
                        "set_environment",
                        None,
                        True,
                        dependency_resolver=self,
                    )
        return NullDependency(version=None, name=name)

    def _get_package_installed_dependency_path(self, installed_tool_dependency, name, version):
        tool_shed_repository = installed_tool_dependency.tool_shed_repository
        base_path = self.base_path
        return join(
            base_path,
            name,
            version,
            tool_shed_repository.owner,
            tool_shed_repository.name,
            tool_shed_repository.installed_changeset_revision,
        )

    def _get_set_environment_installed_dependency_script_path(self, installed_tool_dependency, name):
        tool_shed_repository = installed_tool_dependency.tool_shed_repository
        base_path = self.base_path
        path = abspath(
            join(
                base_path,
                "environment_settings",
                name,
                tool_shed_repository.owner,
                tool_shed_repository.name,
                tool_shed_repository.installed_changeset_revision,
            )
        )
        if exists(path):
            script = join(path, "env.sh")
            return ToolShedDependency(script, path, name, "set_environment", None, True, dependency_resolver=self)
        return NullDependency(version=None, name=name)


__all__ = ("ToolShedPackageDependencyResolver",)
