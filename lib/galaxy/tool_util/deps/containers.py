import collections
import logging
import os
from typing import (
    Any,
    Dict,
    List,
    Optional,
    TYPE_CHECKING,
)

from galaxy.util import (
    asbool,
    plugin_config,
)
from .container_classes import (
    CONTAINER_CLASSES,
    DOCKER_CONTAINER_TYPE,
    NULL_CONTAINER,
    SINGULARITY_CONTAINER_TYPE,
)
from .container_resolvers import ResolutionCache
from .container_resolvers.explicit import (
    ExplicitContainerResolver,
    ExplicitSingularityContainerResolver,
)
from .container_resolvers.mulled import (
    BuildMulledDockerContainerResolver,
    BuildMulledSingularityContainerResolver,
    CachedMulledDockerContainerResolver,
    CachedMulledSingularityContainerResolver,
    MulledDockerContainerResolver,
    MulledSingularityContainerResolver,
)
from .requirements import ContainerDescription

if TYPE_CHECKING:
    from beaker.cache import Cache

    from .dependencies import (
        AppInfo,
        ToolInfo,
    )

log = logging.getLogger(__name__)


DEFAULT_CONTAINER_TYPE = DOCKER_CONTAINER_TYPE
ALL_CONTAINER_TYPES = [DOCKER_CONTAINER_TYPE, SINGULARITY_CONTAINER_TYPE]

ResolvedContainerDescription = collections.namedtuple(
    "ResolvedContainerDescription", ["container_resolver", "container_description"]
)


class ContainerFinder:
    def __init__(self, app_info, mulled_resolution_cache=None):
        self.app_info = app_info
        self.mulled_resolution_cache = mulled_resolution_cache
        self.default_container_registry = ContainerRegistry(app_info, mulled_resolution_cache=mulled_resolution_cache)
        self.destination_container_registeries = {}

    def _enabled_container_types(self, destination_info):
        return [t for t in ALL_CONTAINER_TYPES if self.__container_type_enabled(t, destination_info)]

    def find_best_container_description(self, enabled_container_types, tool_info, **kwds):
        """Regardless of destination properties - find best container for tool.

        Given container types and container.ToolInfo description of the tool."""
        return self.default_container_registry.find_best_container_description(
            enabled_container_types, tool_info, **kwds
        )

    def resolve(self, enabled_container_types, tool_info, **kwds):
        """Regardless of destination properties - find ResolvedContainerDescription for tool."""
        return self.default_container_registry.resolve(enabled_container_types, tool_info, **kwds)

    def _container_registry_for_destination(self, destination_info):
        destination_id = destination_info.get("id")  # Probably not the way to get the ID?
        destination_container_registry = None
        if destination_id and destination_id not in self.destination_container_registeries:
            if "container_resolvers" in destination_info:
                destination_container_registry = ContainerRegistry(
                    self.app_info,
                    destination_info=destination_info,
                    mulled_resolution_cache=self.mulled_resolution_cache,
                )
                self.destination_container_registeries[destination_id] = destination_container_registry
        elif not destination_id and "container_resolvers" in destination_info:
            destination_container_registry = ContainerRegistry(
                self.app_info, destination_info=destination_info, mulled_resolution_cache=self.mulled_resolution_cache
            )

        if (
            destination_container_registry is None
            and destination_id
            and destination_id in self.destination_container_registeries
        ):
            destination_container_registry = self.destination_container_registeries[destination_id]

        return destination_container_registry or self.default_container_registry

    def find_container(self, tool_info, destination_info, job_info):
        enabled_container_types = self._enabled_container_types(destination_info)

        # Short-cut everything else and just skip checks if no container type is enabled.
        if not enabled_container_types:
            return NULL_CONTAINER

        def __destination_container(container_description=None, container_id=None, container_type=None):
            if container_description:
                container_id = container_description.identifier
                container_type = container_description.type
            container = self.__destination_container(
                container_id,
                container_type,
                tool_info,
                destination_info,
                job_info,
                container_description,
            )
            return container

        def container_from_description_from_dicts(destination_container_dicts):
            for destination_container_dict in destination_container_dicts:
                container_description = ContainerDescription.from_dict(destination_container_dict)
                if container_description:
                    container = __destination_container(container_description)
                    if container:
                        return container

        if "container_override" in destination_info:
            container = container_from_description_from_dicts(destination_info["container_override"])
            if container:
                return container

        # If destination forcing Galaxy to use a particular container do it,
        # this is likely kind of a corner case. For instance if deployers
        # do not trust the containers annotated in tools.
        for container_type in CONTAINER_CLASSES.keys():
            container_id = self.__overridden_container_id(container_type, destination_info)
            if container_id:
                container = __destination_container(container_type=container_type, container_id=container_id)
                if container:
                    return container

        # Otherwise lets see if we can find container for the tool.
        container_registry = self._container_registry_for_destination(destination_info)
        container_description = container_registry.find_best_container_description(enabled_container_types, tool_info)
        container = __destination_container(container_description)
        if container:
            return container

        # If we still don't have a container, check to see if any container
        # types define a default container id and use that.
        if "container" in destination_info:
            container = container_from_description_from_dicts(destination_info["container"])
            if container:
                return container

        for container_type in CONTAINER_CLASSES.keys():
            container_id = self.__default_container_id(container_type, destination_info)
            if container_id:
                container = __destination_container(container_type=container_type, container_id=container_id)
                if container:
                    return container

        return NULL_CONTAINER

    def resolution_cache(self):
        return self.default_container_registry.get_resolution_cache()

    def __overridden_container_id(self, container_type, destination_info):
        if not self.__container_type_enabled(container_type, destination_info):
            return None
        if f"{container_type}_container_id_override" in destination_info:
            return destination_info.get(f"{container_type}_container_id_override")
        if f"{container_type}_image_override" in destination_info:
            return self.__build_container_id_from_parts(container_type, destination_info, mode="override")

    def __build_container_id_from_parts(self, container_type, destination_info, mode):
        repo = ""
        owner = ""
        repo_key = f"{container_type}_repo_{mode}"
        owner_key = f"{container_type}_owner_{mode}"
        if repo_key in destination_info:
            repo = f"{destination_info[repo_key]}/"
        if owner_key in destination_info:
            owner = f"{destination_info[owner_key]}/"
        cont_id = repo + owner + destination_info[f"{container_type}_image_{mode}"]
        tag_key = f"{container_type}_tag_{mode}"
        if tag_key in destination_info:
            cont_id += f":{destination_info[tag_key]}"
        return cont_id

    def __default_container_id(self, container_type, destination_info):
        if not self.__container_type_enabled(container_type, destination_info):
            return None
        key = f"{container_type}_default_container_id"
        # Also allow docker_image...
        if key not in destination_info:
            key = f"{container_type}_image"
        if key in destination_info:
            return destination_info.get(key)
        elif f"{container_type}_image_default" in destination_info:
            return self.__build_container_id_from_parts(container_type, destination_info, mode="default")
        return None

    def __destination_container(
        self, container_id, container_type, tool_info, destination_info, job_info, container_description=None
    ):
        # TODO: ensure destination_info is dict-like
        if not self.__container_type_enabled(container_type, destination_info):
            return NULL_CONTAINER

        # TODO: Right now this assumes all containers available when a
        # container type is - there should be more thought put into this.
        # Checking which are available - settings policies for what can be
        # auto-fetched, etc....
        return CONTAINER_CLASSES[container_type](
            container_id, self.app_info, tool_info, destination_info, job_info, container_description
        )

    def __container_type_enabled(self, container_type, destination_info):
        return asbool(destination_info.get(f"{container_type}_enabled", False))


class NullContainerFinder:
    def find_container(self, tool_info, destination_info, job_info):
        return []


class ContainerRegistry:
    """Loop through enabled ContainerResolver plugins and find first match."""

    def __init__(
        self,
        app_info: "AppInfo",
        destination_info: Optional[Dict[str, Any]] = None,
        mulled_resolution_cache: Optional["Cache"] = None,
    ) -> None:
        self.resolver_classes = self.__resolvers_dict()
        self.enable_mulled_containers = app_info.enable_mulled_containers
        self.app_info = app_info
        self.container_resolvers = self.__build_container_resolvers(app_info, destination_info)
        self.mulled_resolution_cache = mulled_resolution_cache

    def __build_container_resolvers(self, app_info, destination_info):
        app_conf_file = getattr(app_info, "container_resolvers_config_file", None)
        app_conf_dict = getattr(app_info, "container_resolvers_config_dict", None)

        if destination_info is not None:
            conf_file = destination_info.get("container_resolvers_config_file", app_conf_file)
            conf_dict = destination_info.get("container_resolvers", app_conf_dict)
        else:
            conf_file = app_conf_file
            conf_dict = app_conf_dict

        plugin_source = None
        if conf_dict:
            log.debug("Loading container resolution config inline from Galaxy or job configuration file")
            plugin_source = plugin_config.plugin_source_from_dict(conf_dict)
        elif conf_file and not os.path.exists(conf_file):
            log.warning(f"Unable to find config file '{conf_file}'")
        elif conf_file:
            log.debug("Loading container resolution config from file '{conf_file}'")
            plugin_source = plugin_config.plugin_source_from_path(conf_file)
        if plugin_source:
            return self._parse_resolver_conf(plugin_source)
        return self.__default_container_resolvers()

    def _parse_resolver_conf(self, plugin_source):
        extra_kwds = {"app_info": self.app_info}
        return plugin_config.load_plugins(self.resolver_classes, plugin_source, extra_kwds)

    def __default_container_resolvers(self):
        default_resolvers = [
            ExplicitContainerResolver(self.app_info),
            ExplicitSingularityContainerResolver(self.app_info),
        ]
        if self.enable_mulled_containers:
            default_resolvers.extend(
                [
                    CachedMulledDockerContainerResolver(self.app_info, namespace="biocontainers"),
                    CachedMulledDockerContainerResolver(self.app_info, namespace="local"),
                    CachedMulledSingularityContainerResolver(self.app_info, namespace="biocontainers"),
                    CachedMulledSingularityContainerResolver(self.app_info, namespace="local"),
                    MulledDockerContainerResolver(self.app_info, namespace="biocontainers"),
                    MulledSingularityContainerResolver(self.app_info, namespace="biocontainers"),
                ]
            )
            # BuildMulledDockerContainerResolver and BuildMulledSingularityContainerResolver both need the docker daemon to build images.
            # If docker is not available, we don't load them.
            build_mulled_docker_container_resolver = BuildMulledDockerContainerResolver(self.app_info)
            if build_mulled_docker_container_resolver.cli_available:
                default_resolvers.extend(
                    [
                        build_mulled_docker_container_resolver,
                        BuildMulledSingularityContainerResolver(self.app_info),
                    ]
                )
        return default_resolvers

    def __resolvers_dict(self):
        import galaxy.tool_util.deps.container_resolvers

        return plugin_config.plugins_dict(galaxy.tool_util.deps.container_resolvers, "resolver_type")

    def get_resolution_cache(self):
        cache = ResolutionCache()
        if self.mulled_resolution_cache is not None:
            cache.mulled_resolution_cache = self.mulled_resolution_cache
        return cache

    def find_best_container_description(
        self, enabled_container_types: List[str], tool_info: "ToolInfo", **kwds: Any
    ) -> Optional[ContainerDescription]:
        """Yield best container description of supplied types matching tool info."""
        try:
            resolved_container_description = self.resolve(enabled_container_types, tool_info, **kwds)
        except Exception:
            log.exception("Could not get container description for tool '%s'", tool_info.tool_id)
            return None
        return None if resolved_container_description is None else resolved_container_description.container_description

    def resolve(
        self,
        enabled_container_types,
        tool_info,
        index=None,
        resolver_type=None,
        install=True,
        resolution_cache=None,
        session=None,
    ):
        resolution_cache = resolution_cache or self.get_resolution_cache()
        for i, container_resolver in enumerate(self.container_resolvers):
            if index is not None and i != index:
                continue

            if resolver_type is not None and resolver_type != container_resolver.resolver_type:
                continue

            if hasattr(container_resolver, "container_type"):
                if container_resolver.container_type not in enabled_container_types:
                    continue

            if not install and container_resolver.builds_on_resolution:
                continue

            container_description = container_resolver.resolve(
                enabled_container_types, tool_info, install=install, resolution_cache=resolution_cache, session=session
            )
            log.info(
                f"Checking with container resolver [{container_resolver}] found description [{container_description}]"
            )
            if container_description:
                assert container_description.type in enabled_container_types
                return ResolvedContainerDescription(container_resolver, container_description)

        return None
