from os.path import join, islink, realpath, basename, exists, abspath

from ..resolvers import DependencyResolver, INDETERMINATE_DEPENDENCY
from galaxy.util import string_as_bool


class GalaxyPackageDependencyResolver(DependencyResolver):

    def __init__(self, dependency_manager, **kwds):
        ## Galaxy tool shed requires explicit versions on XML elements,
        ## this in inconvient for testing or Galaxy instances not utilizing
        ## the tool shed so allow a fallback version of the Galaxy package
        ## resolver that will just grab 'default' version of exact version
        ## unavailable.
        self.versionless = string_as_bool(kwds.get('versionless', "false"))
        self.base_path = abspath( kwds.get('base_path', dependency_manager.default_base_path) )

    def resolve( self, name, version, type, **kwds ):
        """
        Attempt to find a dependency named `name` at version `version`. If version is None, return the "default" version as determined using a
        symbolic link (if found). Returns a triple of: env_script, base_path, real_version
        """
        if version is None or self.versionless:
            return self._find_dep_default( name, type=type, **kwds )
        else:
            return self._find_dep_versioned( name, version, type=type, **kwds )

    def _find_dep_versioned( self, name, version, type='package', **kwds ):
        base_path = self.base_path
        path = join( base_path, name, version )
        return self._galaxy_package_dep(path, version)

    def _find_dep_default( self, name, type='package', **kwds ):
        base_path = self.base_path
        path = join( base_path, name, 'default' )
        if islink( path ):
            real_path = realpath( path )
            real_version = basename( real_path )
            return self._galaxy_package_dep(real_path, real_version)
        else:
            return INDETERMINATE_DEPENDENCY

    def _galaxy_package_dep( self, path, version ):
        script = join( path, 'env.sh' )
        if exists( script ):
            return script, path, version
        elif exists( join( path, 'bin' ) ):
            return None, path, version
        return INDETERMINATE_DEPENDENCY

__all__ = [GalaxyPackageDependencyResolver]
