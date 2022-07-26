"""The module defines the abstract interface for resolving container images for tool execution."""
from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty,
)

from galaxy.util.bunch import Bunch
from galaxy.util.dictifiable import Dictifiable


class ResolutionCache(Bunch):
    """Simple cache for duplicated computation created once per set of requests (likely web request in Galaxy context).

    This should not be assumed to be thread safe - resolution using a given cache should all occur
    one resolution at a time in a single thread.
    """

    mulled_resolution_cache = None


class ContainerResolver(Dictifiable, metaclass=ABCMeta):
    """Description of a technique for resolving container images for tool execution."""

    # Keys for dictification.
    dict_collection_visible_keys = ["resolver_type", "can_uninstall_dependencies", "builds_on_resolution"]
    can_uninstall_dependencies = False
    builds_on_resolution = False
    read_only = True  # not used for containers, but set for when they are used like dependency resolvers

    def __init__(self, app_info=None, **kwds):
        """Default initializer for ``ContainerResolver`` subclasses."""
        self.app_info = app_info
        self.resolver_kwds = kwds

    def _get_config_option(self, key, default=None):
        """Look in resolver-specific settings for option and then fallback to
        global settings.
        """
        if self.app_info and hasattr(self.app_info, key):
            return getattr(self.app_info, key)
        else:
            return default

    @abstractmethod
    def resolve(self, enabled_container_types, tool_info, resolution_cache=None, **kwds):
        """Find a container matching all supplied requirements for tool.

        The supplied argument is a :class:`galaxy.tool_util.deps.containers.ToolInfo` description
        of the tool and its requirements.
        """

    @abstractproperty
    def resolver_type(self):
        """Short label for the type of container resolution."""

    def _container_type_enabled(self, container_description, enabled_container_types):
        """Return a boolean indicating if the specified container type is enabled."""
        return container_description.type in enabled_container_types

    def __str__(self):
        return f"{self.__class__.__name__}[]"
