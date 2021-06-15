"""
Dependency management for tools.
"""

import json
import logging
import os.path
import shutil

from galaxy.util import (
    hash_util,
    plugin_config,
    string_as_bool,
)
from galaxy.util.oset import OrderedSet
from .container_resolvers import ContainerResolver
from .dependencies import ToolInfo
from .requirements import (
    ContainerDescription,
    ToolRequirement,
    ToolRequirements
)
from .resolvers import (
    ContainerDependency,
    NullDependency,
)
from .resolvers.tool_shed_packages import ToolShedPackageDependencyResolver

log = logging.getLogger(__name__)

CONFIG_VAL_NOT_FOUND = object()


def build_dependency_manager(app_config_dict=None, resolution_config_dict=None, conf_file=None, default_tool_dependency_dir=None):
    """Build a DependencyManager object from app and/or resolution config.

    If app_config_dict is specified, it should be application configuration information
    and configuration options are generally named to identify the context of dependency
    management (e.g. conda_prefix not prefix or use_cached_dependency_manager not cache).
    resolution_config_dict if specified is assumed to be the to_dict() version of a
    DependencyManager and should only contain dependency configuration options.
    """

    if app_config_dict is None:
        app_config_dict = {}
    else:
        app_config_dict = app_config_dict.copy()

    tool_dependency_dir = app_config_dict.get("tool_dependency_dir", default_tool_dependency_dir)
    if tool_dependency_dir and tool_dependency_dir.lower() == "none":
        app_config_dict["tool_dependency_dir"] = None

    if resolution_config_dict is None and "dependency_resolution" in app_config_dict:
        resolution_config_dict = app_config_dict["dependency_resolution"]

    if resolution_config_dict:
        # Convert local to_dict options into global ones.

        # to_dict() has "cache", "cache_dir", "use", "default_base_path", "resolvers", "precache"
        app_config_props_from_resolution_config = {
            "use_tool_dependencies": resolution_config_dict.get("use", None),
            "tool_dependency_dir": resolution_config_dict.get("default_base_path", None),
            "dependency_resolvers": resolution_config_dict.get("resolvers", None),
            "tool_dependency_cache_dir": resolution_config_dict.get("cache_dir", None),
            "precache_dependencies": resolution_config_dict.get("precache", None),
            "use_cached_dependency_manager": resolution_config_dict.get("cache", None),
        }

        for key, value in app_config_props_from_resolution_config.items():
            if value is not None:
                app_config_dict[key] = value

    use_tool_dependencies = app_config_dict.get("use_tool_dependencies", None)
    # if we haven't set an explicit True or False, try to infer from config...
    if use_tool_dependencies is None:
        use_tool_dependencies = app_config_dict.get("tool_dependency_dir", default_tool_dependency_dir) is not None or \
            app_config_dict.get("dependency_resolvers") or \
            (conf_file and os.path.exists(conf_file))

    if use_tool_dependencies:
        dependency_manager_kwds = {
            "default_base_path": app_config_dict.get("tool_dependency_dir", default_tool_dependency_dir),
            "conf_file": conf_file,
            "app_config": app_config_dict,
        }
        if string_as_bool(app_config_dict.get("use_cached_dependency_manager")):
            dependency_manager = CachedDependencyManager(**dependency_manager_kwds)
        else:
            dependency_manager = DependencyManager(**dependency_manager_kwds)
    else:
        dependency_manager = NullDependencyManager()

    return dependency_manager


class DependencyManager:
    """
    A DependencyManager attempts to resolve named and versioned dependencies by
    searching for them under a list of directories. Directories should be
    of the form:

        $BASE/name/version/...

    and should each contain a file 'env.sh' which can be sourced to make the
    dependency available in the current shell environment.
    """
    cached = False

    def __init__(self, default_base_path, conf_file=None, app_config=None):
        """
        Create a new dependency manager looking for packages under the paths listed
        in `base_paths`.  The default base path is app.config.tool_dependency_dir.
        """
        if app_config is None:
            app_config = {}
        if not os.path.exists(default_base_path):
            log.warning("Path '%s' does not exist, ignoring", default_base_path)
        if not os.path.isdir(default_base_path):
            log.warning("Path '%s' is not directory, ignoring", default_base_path)
        self.__app_config = app_config
        self.default_base_path = os.path.abspath(default_base_path)
        self.resolver_classes = self.__resolvers_dict()

        plugin_source = None
        dependency_resolver_dicts = app_config.get("dependency_resolvers")
        if dependency_resolver_dicts is not None:
            plugin_source = plugin_config.PluginConfigSource('dict', dependency_resolver_dicts)
        else:
            plugin_source = self.__build_dependency_resolvers_plugin_source(conf_file)
        self.dependency_resolvers = self.__parse_resolver_conf_plugins(plugin_source)
        self._enabled_container_types = []
        self._destination_for_container_type = {}

    def set_enabled_container_types(self, container_types_to_destinations):
        """Set the union of all enabled container types."""
        self._enabled_container_types = [container_type for container_type in container_types_to_destinations.keys()]
        # Just pick first enabled destination for a container type, probably covers the most common deployment scenarios
        self._destination_for_container_type = container_types_to_destinations

    def get_destination_info_for_container_type(self, container_type, destination_id=None):
        if destination_id is None:
            return next(iter(self._destination_for_container_type[container_type])).params
        else:
            for destination in self._destination_for_container_type[container_type]:
                if destination.id == destination_id:
                    return destination.params

    @property
    def enabled_container_types(self):
        """Returns the union of enabled container types."""
        return self._enabled_container_types

    def get_resolver_option(self, resolver, key, explicit_resolver_options=None):
        """Look in resolver-specific settings for option and then fallback to global settings.
        """
        if explicit_resolver_options is None:
            explicit_resolver_options = {}
        default = resolver.config_options.get(key)
        config_prefix = resolver.resolver_type
        global_key = f"{config_prefix}_{key}"
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

    @property
    def precache(self):
        return string_as_bool(self.get_app_option("precache_dependencies", True))

    def dependency_shell_commands(self, requirements, **kwds):
        requirements_to_dependencies = self.requirements_to_dependencies(requirements, **kwds)
        ordered_dependencies = OrderedSet(requirements_to_dependencies.values())
        return [dependency.shell_commands() for dependency in ordered_dependencies if not isinstance(dependency, ContainerDependency)]

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

    def _requirements_to_dependencies_dict(self, requirements, search=False, **kwds):
        """Build simple requirements to dependencies dict for resolution."""
        requirement_to_dependency = {}
        index = kwds.get('index')
        install = kwds.get('install', False)
        resolver_type = kwds.get('resolver_type')
        include_containers = kwds.get('include_containers', False)
        container_type = kwds.get('container_type')
        require_exact = kwds.get('exact', False)
        return_null_dependencies = kwds.get('return_null', False)

        resolvable_requirements = requirements.resolvable

        tool_info_kwds = dict(requirements=resolvable_requirements)
        if 'tool_instance' in kwds:
            tool = kwds['tool_instance']
            tool_info_kwds['tool_id'] = tool.id
            tool_info_kwds['tool_version'] = tool.version
            tool_info_kwds['container_descriptions'] = tool.containers
            tool_info_kwds['requires_galaxy_python_environment'] = tool.requires_galaxy_python_environment

        tool_info = ToolInfo(**tool_info_kwds)

        for i, resolver in enumerate(self.dependency_resolvers):

            if index is not None and i != index:
                continue

            if resolver_type is not None and resolver.resolver_type != resolver_type:
                continue

            if container_type is not None and getattr(resolver, "container_type", None) != container_type:
                continue

            _requirement_to_dependency = {k: v for k, v in requirement_to_dependency.items() if not isinstance(v, NullDependency)}

            if len(_requirement_to_dependency) == len(resolvable_requirements):
                # Shortcut - resolution complete.
                break

            # Check requirements all at once
            all_unmet = len(_requirement_to_dependency) == 0
            if hasattr(resolver, "resolve_all"):
                resolve = resolver.resolve_all
            elif isinstance(resolver, ContainerResolver):
                if not include_containers:
                    continue
                if not install and resolver.builds_on_resolution:
                    # don't want to build images here
                    continue
                if not resolver.resolver_type.startswith(('cached', 'explicit', 'fallback')) and not (search or install):
                    # These would look up available containers using the quay API,
                    # we only want to do this if we search for containers
                    continue
                resolve = resolver.resolve
            else:
                resolve = None
            if all_unmet and resolve is not None:
                # TODO: Handle specs.
                dependencies = resolve(requirements=resolvable_requirements,
                                       enabled_container_types=self.enabled_container_types,
                                       destination_for_container_type=self.get_destination_info_for_container_type,
                                       tool_info=tool_info,
                                       **kwds)
                if dependencies:
                    if isinstance(dependencies, ContainerDescription):
                        dependencies = [ContainerDependency(dependencies, name=r.name, version=r.version, container_resolver=resolver) for r in resolvable_requirements]
                    assert len(dependencies) == len(resolvable_requirements)
                    for requirement, dependency in zip(resolvable_requirements, dependencies):
                        log.debug(dependency.resolver_msg)
                        requirement_to_dependency[requirement] = dependency

                    # Shortcut - resolution complete.
                    break

            if not isinstance(resolver, ContainerResolver):

                # Check individual requirements
                for requirement in resolvable_requirements:
                    if requirement in _requirement_to_dependency:
                        continue

                    dependency = resolver.resolve(requirement, **kwds)
                    if require_exact and not dependency.exact:
                        continue

                    if not isinstance(dependency, NullDependency):
                        log.debug(dependency.resolver_msg)
                        requirement_to_dependency[requirement] = dependency
                    elif return_null_dependencies:
                        log.debug(dependency.resolver_msg)
                        dependency.version = requirement.version
                        requirement_to_dependency[requirement] = dependency

        return requirement_to_dependency

    def uses_tool_shed_dependencies(self):
        return any(map(lambda r: isinstance(r, ToolShedPackageDependencyResolver), self.dependency_resolvers))

    def find_dep(self, name, version=None, type='package', **kwds):
        log.debug(f'Find dependency {name} version {version}')
        requirements = ToolRequirements([ToolRequirement(name=name, version=version, type=type)])
        dep_dict = self._requirements_to_dependencies_dict(requirements, **kwds)
        if len(dep_dict) > 0:
            return next(iter(dep_dict.values()))  # get first dep
        else:
            return NullDependency(name=name, version=version)

    def __build_dependency_resolvers_plugin_source(self, conf_file):
        if not conf_file:
            return self.__default_dependency_resolvers_source()
        if not os.path.exists(conf_file):
            log.debug("Unable to find config file '%s'", conf_file)
            return self.__default_dependency_resolvers_source()
        plugin_source = plugin_config.plugin_source_from_path(conf_file)
        return plugin_source

    def __default_dependency_resolvers_source(self):
        return plugin_config.PluginConfigSource('dict', [
            {"type": "tool_shed_packages"},
            {"type": "galaxy_packages"},
            {"type": "conda"},
            {"type": "galaxy_packages", "versionless": True},
            {"type": "conda", "versionless": True},
        ])

    def __parse_resolver_conf_plugins(self, plugin_source):
        """
        """
        extra_kwds = dict(dependency_manager=self)
        # Use either 'type' from YAML definition or 'resolver_type' from to_dict definition.
        return plugin_config.load_plugins(self.resolver_classes, plugin_source, extra_kwds, plugin_type_keys=['type', 'resolver_type'])

    def __resolvers_dict(self):
        import galaxy.tool_util.deps.resolvers
        return plugin_config.plugins_dict(galaxy.tool_util.deps.resolvers, 'resolver_type')

    def to_dict(self):
        return {
            "use": True,
            "cache": self.cached,
            "precache": self.precache,
            "cache_dir": getattr(self, "tool_dependency_cache_dir", None),
            "default_base_path": self.default_base_path,
            "resolvers": [m.to_dict() for m in self.dependency_resolvers],
        }


class CachedDependencyManager(DependencyManager):
    cached = True

    def __init__(self, default_base_path, **kwd):
        super().__init__(default_base_path=default_base_path, **kwd)
        self.tool_dependency_cache_dir = self.get_app_option("tool_dependency_cache_dir") or os.path.join(default_base_path, "_cache")

    def build_cache(self, requirements, **kwds):
        resolved_dependencies = self.requirements_to_dependencies(requirements, **kwds)
        cacheable_dependencies = [dep for dep in resolved_dependencies.values() if dep.cacheable]
        hashed_dependencies_dir = self.get_hashed_dependencies_path(cacheable_dependencies)
        if os.path.exists(hashed_dependencies_dir):
            if kwds.get('force_rebuild', False):
                try:
                    shutil.rmtree(hashed_dependencies_dir)
                except Exception:
                    log.warning(f"Could not delete cached dependencies directory '{hashed_dependencies_dir}'")
                    raise
            else:
                log.debug("Cached dependencies directory '%s' already exists, skipping build", hashed_dependencies_dir)
                return
        [dep.build_cache(hashed_dependencies_dir) for dep in cacheable_dependencies]

    def dependency_shell_commands(self, requirements, **kwds):
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
        if not os.path.exists(hashed_dependencies_dir) and self.precache:
            # Cache not present, try to create it
            self.build_cache(requirements, **kwds)
        if os.path.exists(hashed_dependencies_dir):
            [dep.set_cache_path(hashed_dependencies_dir) for dep in cacheable_dependencies]
        commands = [dep.shell_commands() for dep in resolved_dependencies.values()]
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


class NullDependencyManager(DependencyManager):
    cached = False

    def __init__(self, default_base_path=None, conf_file=None, app_config=None):
        if app_config is None:
            app_config = {}
        self.__app_config = app_config
        self.resolver_classes = set()
        self.dependency_resolvers = []
        self._enabled_container_types = []
        self._destination_for_container_type = {}
        self.default_base_path = None

    def uses_tool_shed_dependencies(self):
        return False

    def dependency_shell_commands(self, requirements, **kwds):
        return []

    def find_dep(self, name, version=None, type='package', **kwds):
        return NullDependency(version=version, name=name)

    def to_dict(self):
        return {"use": False}
