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

from .requirements import (
    ToolRequirement,
    ToolRequirements
)
from .resolvers import NullDependency
from .resolvers.conda import CondaDependencyResolver
from .resolvers.galaxy_packages import GalaxyPackageDependencyResolver
from .resolvers.tool_shed_packages import ToolShedPackageDependencyResolver

log = logging.getLogger( __name__ )

CONFIG_VAL_NOT_FOUND = object()


def build_dependency_manager( config ):
    if getattr( config, "use_tool_dependencies", False ):
        dependency_manager_kwds = {
            'default_base_path': config.tool_dependency_dir,
            'conf_file': config.dependency_resolvers_config_file,
            'app_config': config,
        }
        if getattr(config, "use_cached_dependency_manager", False):
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
    def __init__( self, default_base_path, conf_file=None, app_config={} ):
        """
        Create a new dependency manager looking for packages under the paths listed
        in `base_paths`.  The default base path is app.config.tool_dependency_dir.
        """
        if not os.path.exists( default_base_path ):
            log.warning( "Path '%s' does not exist, ignoring", default_base_path )
        if not os.path.isdir( default_base_path ):
            log.warning( "Path '%s' is not directory, ignoring", default_base_path )
        self.__app_config = app_config
        self.default_base_path = os.path.abspath( default_base_path )
        self.resolver_classes = self.__resolvers_dict()
        self.dependency_resolvers = self.__build_dependency_resolvers( conf_file )

    def get_resolver_option(self, resolver, key, explicit_resolver_options={}):
        """Look in resolver-specific settings for option and then fallback to global settings.
        """
        default = resolver.config_options.get(key)
        config_prefix = resolver.resolver_type
        global_key = "%s_%s" % (config_prefix, key)
        value = explicit_resolver_options.get(key, CONFIG_VAL_NOT_FOUND)
        if value is CONFIG_VAL_NOT_FOUND:
            value = self.get_app_option(global_key, default)

        return value

    def get_app_option(self, key, default=None):
        value = CONFIG_VAL_NOT_FOUND
        if isinstance(self.__app_config, dict):
            value = self.__app_config.get(key, CONFIG_VAL_NOT_FOUND)
        else:
            value = getattr(self.__app_config, key, CONFIG_VAL_NOT_FOUND)
        if value is CONFIG_VAL_NOT_FOUND and hasattr(self.__app_config, "config_dict"):
            value = self.__app_config.config_dict.get(key, CONFIG_VAL_NOT_FOUND)
        if value is CONFIG_VAL_NOT_FOUND:
            value = default
        return value

    def dependency_shell_commands( self, requirements, **kwds ):
        requirement_to_dependency = self.requirements_to_dependencies(requirements, **kwds)
        return [dependency.shell_commands(requirement) for requirement, dependency in requirement_to_dependency.items()]

    def requirements_to_dependencies(self, requirements, **kwds):
        """
        Takes a list of requirements and returns a dictionary
        with requirements as key and dependencies as value caching
        these on the tool instance if supplied.
        """
        requirement_to_dependency = self._requirements_to_dependencies_dict(requirements, **kwds)

        if 'tool_instance' in kwds:
            kwds['tool_instance'].dependencies = [dep.to_dict() for dep in requirement_to_dependency.values()]

        return requirement_to_dependency

    def _requirements_to_dependencies_dict(self, requirements, **kwds):
        """Build simple requirements to dependencies dict for resolution."""
        requirement_to_dependency = OrderedDict()
        index = kwds.get('index', None)
        require_exact = kwds.get('exact', False)
        return_null_dependencies = kwds.get('return_null', False)

        resolvable_requirements = requirements.resolvable

        for i, resolver in enumerate(self.dependency_resolvers):
            if index is not None and i != index:
                continue

            if len(requirement_to_dependency) == len(resolvable_requirements):
                # Shortcut - resolution complete.
                break

            # Check requirements all at once
            all_unmet = len(requirement_to_dependency) == 0
            if all_unmet and hasattr(resolver, "resolve_all"):
                # TODO: Handle specs.
                dependencies = resolver.resolve_all(resolvable_requirements, **kwds)
                if dependencies:
                    assert len(dependencies) == len(resolvable_requirements)
                    for requirement, dependency in zip(resolvable_requirements, dependencies):
                        log.debug(dependency.resolver_msg)
                        requirement_to_dependency[requirement] = dependency

                    # Shortcut - resolution complete.
                    break

            # Check individual requirements
            for requirement in resolvable_requirements:
                if requirement in requirement_to_dependency:
                    continue

                dependency = resolver.resolve( requirement, **kwds )
                if require_exact and not dependency.exact:
                    continue

                if not isinstance(dependency, NullDependency):
                    log.debug(dependency.resolver_msg)
                    requirement_to_dependency[requirement] = dependency
                elif return_null_dependencies and (resolver == self.dependency_resolvers[-1] or i == index):
                    log.debug(dependency.resolver_msg)
                    requirement_to_dependency[requirement] = dependency

        return requirement_to_dependency

    def uses_tool_shed_dependencies(self):
        return any( map( lambda r: isinstance( r, ToolShedPackageDependencyResolver ), self.dependency_resolvers ) )

    def find_dep( self, name, version=None, type='package', **kwds ):
        log.debug('Find dependency %s version %s' % (name, version))
        requirements = ToolRequirements([ToolRequirement(name=name, version=version, type=type)])
        dep_dict = self._requirements_to_dependencies_dict(requirements, **kwds)
        if len(dep_dict) > 0:
            return dep_dict.values()[0]
        else:
            return NullDependency(name=name, version=version)

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
            CondaDependencyResolver(self),
            GalaxyPackageDependencyResolver(self, versionless=True),
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
    def __init__(self, default_base_path, conf_file=None, app_config={}, tool_dependency_cache_dir=None):
        super(CachedDependencyManager, self).__init__(default_base_path=default_base_path, conf_file=conf_file, app_config=app_config)
        self.tool_dependency_cache_dir = self.get_app_option("tool_dependency_cache_dir")

    def build_cache(self, requirements, **kwds):
        resolved_dependencies = self.requirements_to_dependencies(requirements, **kwds)
        cacheable_dependencies = [dep for dep in resolved_dependencies.values() if dep.cacheable]
        hashed_dependencies_dir = self.get_hashed_dependencies_path(cacheable_dependencies)
        if os.path.exists(hashed_dependencies_dir):
            if kwds.get('force_rebuild', False):
                try:
                    shutil.rmtree(hashed_dependencies_dir)
                except Exception:
                    log.warning("Could not delete cached dependencies directory '%s'" % hashed_dependencies_dir)
                    raise
            else:
                log.debug("Cached dependencies directory '%s' already exists, skipping build", hashed_dependencies_dir)
                return
        [dep.build_cache(hashed_dependencies_dir) for dep in cacheable_dependencies]

    def dependency_shell_commands( self, requirements, **kwds ):
        """
        Runs a set of requirements through the dependency resolvers and returns
        a list of commands required to activate the dependencies. If dependencies
        are cacheable and the cache does not exist, will try to create it.
        If cached environment exists or is successfully created, will generate
        commands to activate it.
        """
        resolved_dependencies = self.requirements_to_dependencies(requirements, **kwds)
        cacheable_dependencies = [dep for dep in resolved_dependencies.values() if dep.cacheable]
        hashed_dependencies_dir = self.get_hashed_dependencies_path(cacheable_dependencies)
        if not os.path.exists(hashed_dependencies_dir) and self.get_app_option("precache_dependencies", False):
            # Cache not present, try to create it
            self.build_cache(requirements, **kwds)
        if os.path.exists(hashed_dependencies_dir):
            [dep.set_cache_path(hashed_dependencies_dir) for dep in cacheable_dependencies]
        commands = [dep.shell_commands(req) for req, dep in resolved_dependencies.items()]
        return commands

    def hash_dependencies(self, resolved_dependencies):
        """Return hash for dependencies"""
        resolved_dependencies = [(dep.name, dep.version, dep.exact, dep.dependency_type) for dep in resolved_dependencies]
        hash_str = json.dumps(sorted(resolved_dependencies))
        return hash_util.new_secure_hash(hash_str)[:8]  # short hash

    def get_hashed_dependencies_path(self, resolved_dependencies):
        """
        Returns the path to the hashed dependencies directory (but does not evaluate whether the path exists).

        :param resolved_dependencies: list of resolved dependencies
        :type resolved_dependencies: list

        :return: path
        :rtype: str
        """
        req_hashes = self.hash_dependencies(resolved_dependencies)
        return os.path.abspath(os.path.join(self.tool_dependency_cache_dir, req_hashes))
