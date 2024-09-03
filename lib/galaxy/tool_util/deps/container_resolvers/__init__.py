"""The module defines the abstract interface for resolving container images for tool execution."""

from abc import (
    ABCMeta,
    abstractmethod,
)
from typing import (
    Any,
    Container,
    Optional,
    TYPE_CHECKING,
)

from galaxy.util.bunch import Bunch
from galaxy.util.dictifiable import Dictifiable

if TYPE_CHECKING:
    from beaker.cache import Cache

    from ..dependencies import (
        AppInfo,
        ToolInfo,
    )
    from ..requirements import ContainerDescription


class ResolutionCache(Bunch):
    """Simple cache for duplicated computation created once per set of requests (likely web request in Galaxy context).

    This should not be assumed to be thread safe - resolution using a given cache should all occur
    one resolution at a time in a single thread.
    """

    mulled_resolution_cache: Optional["Cache"] = None


class ContainerResolver(Dictifiable, metaclass=ABCMeta):
    """Description of a technique for resolving container images for tool execution."""

    # Keys for dictification.
    dict_collection_visible_keys = ["resolver_type", "can_uninstall_dependencies", "builds_on_resolution"]
    can_uninstall_dependencies = False
    builds_on_resolution = False
    read_only = True  # not used for containers, but set for when they are used like dependency resolvers

    def __init__(self, app_info: "AppInfo", **kwds) -> None:
        """Default initializer for ``ContainerResolver`` subclasses."""
        self.app_info = app_info
        self.resolver_kwds = kwds

    def _get_config_option(self, key: str, default: Any = None) -> Any:
        """Look in resolver-specific settings for option and then fallback to
        global settings.
        """
        return getattr(self.app_info, key, default)

    @abstractmethod
    def resolve(
        self, enabled_container_types: Container[str], tool_info: "ToolInfo", **kwds
    ) -> Optional["ContainerDescription"]:
        """Find a container matching all supplied requirements for tool.

        The supplied argument is a :class:`galaxy.tool_util.deps.dependencies.ToolInfo` description
        of the tool and its requirements.
        """

    @property
    @abstractmethod
    def resolver_type(self) -> str:
        """Short label for the type of container resolution."""

    def _container_type_enabled(
        self, container_description: "ContainerDescription", enabled_container_types: Container[str]
    ) -> bool:
        """Return a boolean indicating if the specified container type is enabled."""
        return container_description.type in enabled_container_types

    def __str__(self) -> str:
        return f"{self.__class__.__name__}[]"
