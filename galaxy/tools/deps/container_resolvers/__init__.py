"""The module defines the abstract interface for resolving container images for tool execution."""
from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty,
)

from galaxy.util.dictifiable import Dictifiable


class ContainerResolver(Dictifiable, object):
    """Description of a technique for resolving container images for tool execution."""

    # Keys for dictification.
    dict_collection_visible_keys = ['resolver_type']

    __metaclass__ = ABCMeta

    @abstractmethod
    def resolve(self, tool_info):
        """Find a container matching all supplied requirements for tool.

        The supplied argument is a :class:`galaxy.tools.deps.containers.ToolInfo` description
        of the tool and its requirements.
        """

    @abstractproperty
    def resolver_type(self):
        """Short label for the type of container resolution."""

    def _container_type_enabled(self, container_description, enabled_container_types):
        """Return a boolean indicating if the specified container type is enabled."""
        return container_description.type in enabled_container_types
