from os.path import abspath, join, exists

from .resolver_mixins import UsesInstalledRepositoriesMixin
from .galaxy_packages import GalaxyPackageDependencyResolver, GalaxyPackageDependency
from ..resolvers import INDETERMINATE_DEPENDENCY


class ToolShedPackageDependencyResolver(GalaxyPackageDependencyResolver, UsesInstalledRepositoriesMixin):
    resolver_type = "tool_shed_packages"

    def __init__(self, dependency_manager, **kwds):
        super(ToolShedPackageDependencyResolver, self).__init__(dependency_manager, **kwds)

    def _find_dep_versioned( self, name, version, type='package', **kwds ):
        installed_tool_dependency = self._get_installed_dependency( name, type, version=version, **kwds )
        if installed_tool_dependency:
            path = self._get_package_installed_dependency_path( installed_tool_dependency, name, version )
            return self._galaxy_package_dep(path, version)
        else:
            return INDETERMINATE_DEPENDENCY

    def _find_dep_default( self, name, type='package', **kwds ):
        if type == 'set_environment' and kwds.get('installed_tool_dependencies', None):
            installed_tool_dependency = self._get_installed_dependency( name, type, version=None, **kwds )
            if installed_tool_dependency:
                dependency = self._get_set_environment_installed_dependency_script_path( installed_tool_dependency, name )
                is_galaxy_dep = isinstance(dependency, GalaxyPackageDependency)
                has_script_dep = is_galaxy_dep and dependency.script and dependency.path
                if has_script_dep:
                    # Environment settings do not use versions.
                    return GalaxyPackageDependency(dependency.script, dependency.path, None)
        return INDETERMINATE_DEPENDENCY

    def _get_package_installed_dependency_path( self, installed_tool_dependency, name, version ):
        tool_shed_repository = installed_tool_dependency.tool_shed_repository
        base_path = self.base_path
        return join(
            base_path,
            name,
            version,
            tool_shed_repository.owner,
            tool_shed_repository.name,
            tool_shed_repository.installed_changeset_revision
        )

    def _get_set_environment_installed_dependency_script_path( self, installed_tool_dependency, name ):
        tool_shed_repository = installed_tool_dependency.tool_shed_repository
        base_path = self.base_path
        path = abspath( join( base_path,
                              'environment_settings',
                              name,
                              tool_shed_repository.owner,
                              tool_shed_repository.name,
                              tool_shed_repository.installed_changeset_revision ) )
        if exists( path ):
            script = join( path, 'env.sh' )
            return GalaxyPackageDependency(script, path, None)
        return INDETERMINATE_DEPENDENCY


__all__ = ['ToolShedPackageDependencyResolver']
