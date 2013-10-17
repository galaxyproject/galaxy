"""
Dependency management for tools.
"""

import os.path

import logging
log = logging.getLogger( __name__ )

INDETERMINATE_DEPENDENCY = (None, None, None)


class DependencyManager( object ):
    """
    A DependencyManager attempts to resolve named and versioned dependencies by
    searching for them under a list of directories. Directories should be
    of the form:

        $BASE/name/version/...

    and should each contain a file 'env.sh' which can be sourced to make the
    dependency available in the current shell environment.
    """
    def __init__( self, default_base_path ):
        """
        Create a new dependency manager looking for packages under the paths listed
        in `base_paths`.  The default base path is app.config.tool_dependency_dir.
        """
        if not os.path.exists( default_base_path ):
            log.warn( "Path '%s' does not exist, ignoring", default_base_path )
        if not os.path.isdir( default_base_path ):
            log.warn( "Path '%s' is not directory, ignoring", default_base_path )
        self.default_base_path = os.path.abspath( default_base_path )
        self.dependency_resolvers = [
            ToolShedPackageDependencyResolver(self),
            GalaxyPackageDependencyResolver(self),
        ]


    def find_dep( self, name, version=None, type='package', **kwds ):
        for resolver in self.dependency_resolvers:
            dependency = resolver.resolve( name, version, type, **kwds )
            if dependency != INDETERMINATE_DEPENDENCY:
                return dependency
        return INDETERMINATE_DEPENDENCY


class DependencyResolver(object):

    def resolve( self, name, version, type, **kwds ):
        raise NotImplementedError()


class GalaxyPackageDependencyResolver(DependencyResolver):

    def __init__(self, dependency_manager):
        self.default_base_path = dependency_manager.default_base_path

    def resolve( self, name, version, type, **kwds ):
        """
        Attempt to find a dependency named `name` at version `version`. If version is None, return the "default" version as determined using a
        symbolic link (if found). Returns a triple of: env_script, base_path, real_version
        """
        if version is None:
            return self._find_dep_default( name, type=type, **kwds )
        else:
            return self._find_dep_versioned( name, version, type=type, **kwds )

    def _find_dep_versioned( self, name, version, type='package', **kwds ):
        base_path = self.default_base_path
        path = os.path.join( base_path, name, version )
        return self._galaxy_package_dep(path, version)

    def _find_dep_default( self, name, type='package', **kwds ):
        base_path = self.default_base_path
        path = os.path.join( base_path, name, 'default' )
        if os.path.islink( path ):
            real_path = os.path.realpath( path )
            real_version = os.path.basename( real_path )
            return self._galaxy_package_dep(real_path, real_version)
        else:
            return INDETERMINATE_DEPENDENCY

    def _galaxy_package_dep( self, path, version ):
        script = os.path.join( path, 'env.sh' )
        if os.path.exists( script ):
            return script, path, version
        elif os.path.exists( os.path.join( path, 'bin' ) ):
            return None, path, version
        return INDETERMINATE_DEPENDENCY


class ToolShedPackageDependencyResolver(GalaxyPackageDependencyResolver):

    def __init__(self, dependency_manager):
        super(ToolShedPackageDependencyResolver, self).__init__(dependency_manager)

    def _find_dep_versioned( self, name, version, type='package', **kwds ):
        installed_tool_dependency = self._get_installed_dependency( name, type, version=version, **kwds )
        base_path = self.default_base_path
        if installed_tool_dependency:
            path = self._get_package_installed_dependency_path( installed_tool_dependency, base_path, name, version )
            return self._galaxy_package_dep(path, version)
        else:
            return INDETERMINATE_DEPENDENCY

    def _find_dep_default( self, name, type='package', **kwds ):
        if type == 'set_environment' and kwds.get('installed_tool_dependencies', None):
            installed_tool_dependency = self._get_installed_dependency( name, type, version=None, **kwds )
            if installed_tool_dependency:
                script, path, version = self._get_set_environment_installed_dependency_script_path( installed_tool_dependency, name )
                if script and path:
                    # Environment settings do not use versions.
                    return script, path, None
        return INDETERMINATE_DEPENDENCY

    def _get_installed_dependency( self, name, type, version=None, **kwds ):
        for installed_tool_dependency in kwds.get("installed_tool_dependencies", []):
            name_and_type_equal = installed_tool_dependency.name == name and installed_tool_dependency.type == type
            if version:
                if name_and_type_equal and installed_tool_dependency.version == version:
                    return installed_tool_dependency
            else:
                if name_and_type_equal:
                    return installed_tool_dependency
        return None

    def _get_package_installed_dependency_path( self, installed_tool_dependency, base_path, name, version ):
        tool_shed_repository = installed_tool_dependency.tool_shed_repository
        return os.path.join( base_path,
                             name,
                             version,
                             tool_shed_repository.owner,
                             tool_shed_repository.name,
                             tool_shed_repository.installed_changeset_revision )

    def _get_set_environment_installed_dependency_script_path( self, installed_tool_dependency, name ):
        tool_shed_repository = installed_tool_dependency.tool_shed_repository
        base_path = self.default_base_path
        path = os.path.abspath( os.path.join( base_path,
                                              'environment_settings',
                                              name,
                                              tool_shed_repository.owner,
                                              tool_shed_repository.name,
                                              tool_shed_repository.installed_changeset_revision ) )
        if os.path.exists( path ):
            script = os.path.join( path, 'env.sh' )
            return script, path, None
        return INDETERMINATE_DEPENDENCY
