"""
Dependency management for tools.
"""

import json
import logging
import os.path
import shutil

from collections import OrderedDict

from galaxy.util import (
    hash_util,
    plugin_config
)

from .resolvers import NullDependency
from .resolvers.conda import CondaDependencyResolver, DEFAULT_ENSURE_CHANNELS
from .resolvers.galaxy_packages import GalaxyPackageDependencyResolver
from .resolvers.tool_shed_packages import ToolShedPackageDependencyResolver

log = logging.getLogger( __name__ )

# TODO: Load these from the plugins. Would require a two step initialization of
# DependencyManager - where the plugins are loaded first and then the config
# is parsed and sent through.
EXTRA_CONFIG_KWDS = {
    'conda_prefix': None,
    'conda_exec': None,
    'conda_debug': None,
    'conda_ensure_channels': DEFAULT_ENSURE_CHANNELS,
    'conda_auto_install': False,
    'conda_auto_init': False,
    'conda_copy_dependencies': False,
}

CONFIG_VAL_NOT_FOUND = object()


def build_dependency_manager( config ):
    if getattr( config, "use_tool_dependencies", False ):
        dependency_manager_kwds = {
            'default_base_path': config.tool_dependency_dir,
            'conf_file': config.dependency_resolvers_config_file,
        }
        for key, default_value in EXTRA_CONFIG_KWDS.items():
            value = getattr(config, key, CONFIG_VAL_NOT_FOUND)
            if value is CONFIG_VAL_NOT_FOUND and hasattr(config, "config_dict"):
                value = config.config_dict.get(key, CONFIG_VAL_NOT_FOUND)
            if value is CONFIG_VAL_NOT_FOUND:
                value = default_value
            dependency_manager_kwds[key] = value
        if config.use_cached_dependency_manager:
            dependency_manager_kwds['tool_dependency_cache_dir'] = config.tool_dependency_cache_dir
            dependency_manager = CachedDependencyManager(**dependency_manager_kwds)
        else:
            dependency_manager = DependencyManager( **dependency_manager_kwds )
    else:
        dependency_manager = NullDependencyManager()

    return dependency_manager


class NullDependencyManager( object ):
    dependency_resolvers = []

    def uses_tool_shed_dependencies(self):
        return False

    def dependency_shell_commands( self, requirements, **kwds ):
        return []

    def find_dep( self, name, version=None, type='package', **kwds ):
        return NullDependency(version=version, name=name)


class DependencyManager( object ):
    """
    A DependencyManager attempts to resolve named and versioned dependencies by
    searching for them under a list of directories. Directories should be
    of the form:

        $BASE/name/version/...

    and should each contain a file 'env.sh' which can be sourced to make the
    dependency available in the current shell environment.
    """
    def __init__( self, default_base_path, conf_file=None, **extra_config ):
        """
        Create a new dependency manager looking for packages under the paths listed
        in `base_paths`.  The default base path is app.config.tool_dependency_dir.
        """
        if not os.path.exists( default_base_path ):
            log.warning( "Path '%s' does not exist, ignoring", default_base_path )
        if not os.path.isdir( default_base_path ):
            log.warning( "Path '%s' is not directory, ignoring", default_base_path )
        self.extra_config = extra_config
        self.default_base_path = os.path.abspath( default_base_path )
        self.resolver_classes = self.__resolvers_dict()
        self.dependency_resolvers = self.__build_dependency_resolvers( conf_file )

    def dependency_shell_commands( self, requirements, **kwds ):
        requirement_to_dependency = self.requirements_to_dependencies(requirements, **kwds)
        return [dependency.shell_commands(requirement) for requirement, dependency in requirement_to_dependency.items()]

    def requirements_to_dependencies(self, requirements, **kwds):
        """
        Takes a list of requirements and returns a dictionary
        with requirements as key and dependencies as value.
        """
        requirement_to_dependency = OrderedDict()
        for requirement in requirements:
            if requirement.type in [ 'package', 'set_environment' ]:
                dependency = self.find_dep( name=requirement.name,
                                            version=requirement.version,
                                            type=requirement.type,
                                            **kwds )
                log.debug(dependency.resolver_msg)
                if dependency.dependency_type:
                    requirement_to_dependency[requirement] = dependency
        if 'tool_instance' in kwds:
            kwds['tool_instance'].dependencies = [dep.to_dict() for dep in requirement_to_dependency.values()]
        return requirement_to_dependency

    def uses_tool_shed_dependencies(self):
        return any( map( lambda r: isinstance( r, ToolShedPackageDependencyResolver ), self.dependency_resolvers ) )

    def find_dep( self, name, version=None, type='package', **kwds ):
        log.debug('Find dependency %s version %s' % (name, version))
        index = kwds.get('index', None)
        require_exact = kwds.get('exact', False)
        for i, resolver in enumerate(self.dependency_resolvers):
            if index is not None and i != index:
                continue
            dependency = resolver.resolve( name, version, type, **kwds )
            if require_exact and not dependency.exact:
                continue
            if not isinstance(dependency, NullDependency):
                return dependency
        return NullDependency(version=version, name=name)

    def __build_dependency_resolvers( self, conf_file ):
        if not conf_file:
            return self.__default_dependency_resolvers()
        if not os.path.exists( conf_file ):
            log.debug( "Unable to find config file '%s'", conf_file)
            return self.__default_dependency_resolvers()
        plugin_source = plugin_config.plugin_source_from_path( conf_file )
        return self.__parse_resolver_conf_xml( plugin_source )

    def __default_dependency_resolvers( self ):
        return [
            ToolShedPackageDependencyResolver(self),
            GalaxyPackageDependencyResolver(self),
            GalaxyPackageDependencyResolver(self, versionless=True),
            CondaDependencyResolver(self),
            CondaDependencyResolver(self, versionless=True),
        ]

    def __parse_resolver_conf_xml(self, plugin_source):
        """
        """
        extra_kwds = dict( dependency_manager=self )
        return plugin_config.load_plugins( self.resolver_classes, plugin_source, extra_kwds )

    def __resolvers_dict( self ):
        import galaxy.tools.deps.resolvers
        return plugin_config.plugins_dict( galaxy.tools.deps.resolvers, 'resolver_type' )


class CachedDependencyManager(DependencyManager):
    def __init__(self, default_base_path, conf_file=None, **extra_config):
        super(CachedDependencyManager, self).__init__(default_base_path=default_base_path, conf_file=conf_file, **extra_config)

    def build_cache(self, requirements, **kwds):
        resolved_dependencies = self.requirements_to_dependencies(requirements, **kwds)
        cacheable_dependencies = [dep for req, dep in resolved_dependencies.items() if dep.cacheable]
        hashed_requirements_dir = self.get_hashed_requirements_path(cacheable_dependencies)
        if kwds.get('force_rebuild', False) and os.path.exists(hashed_requirements_dir):
            try:
                shutil.rmtree(hashed_requirements_dir)
            except Exception:
                log.warning("Could not delete cached requirements directory '%s'" % hashed_requirements_dir)
                pass
        [dep.build_cache(hashed_requirements_dir) for dep in cacheable_dependencies]

    def dependency_shell_commands( self, requirements, **kwds ):
        """
        Runs a set of requirements through the dependency resolvers and returns
        a list of commands required to activate the dependencies. If dependencies
        are cacheable and the cache exists, will generate commands to activate
        cached environments.
        """
        resolved_dependencies = self.requirements_to_dependencies(requirements, **kwds)
        cacheable_dependencies = [dep for req, dep in resolved_dependencies.items() if dep.cacheable]
        hashed_requirements_dir = self.get_hashed_requirements_path(cacheable_dependencies)
        if os.path.exists(hashed_requirements_dir):
            [dep.set_cache_path(hashed_requirements_dir) for dep in cacheable_dependencies]
        commands = [dep.shell_commands(req) for req, dep in resolved_dependencies.items()]
        return commands

    def hash_requirements(self, resolved_dependencies):
        """Return hash for requirements"""
        resolved_dependencies = [(dep.name, dep.version, dep.exact, dep.dependency_type) for dep in resolved_dependencies]
        hash_str = json.dumps(sorted(resolved_dependencies))
        return hash_util.new_secure_hash(hash_str)[:8]  # short hash

    def get_hashed_requirements_path(self, resolved_dependencies):
        """
        Returns the path to the hashed requirements directory (but does not evaluate whether the path exists)
        :param requirements:
        :return:
        """
        req_hashes = self.hash_requirements(resolved_dependencies)
        return os.path.join(self.extra_config['tool_dependency_cache_dir'], req_hashes)
