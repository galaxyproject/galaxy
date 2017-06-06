"""The module defines the abstract interface for resolving container images for tool execution."""
from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty,
)

import six

from galaxy.util.dictifiable import Dictifiable


@six.python_2_unicode_compatible
@six.add_metaclass(ABCMeta)
class ContainerResolver(Dictifiable, object):
    """Description of a technique for resolving container images for tool execution."""

    # Keys for dictification.
    dict_collection_visible_keys = ['resolver_type']

    def __init__(self, app_info=None, **kwds):
        """Default initializer for ``ContainerResolver`` subclasses."""
        self.app_info = app_info
        self.resolver_kwds = kwds

    def _get_config_option(self, key, default=None, config_prefix=None, **kwds):
        """Look in resolver-specific settings for option and then fallback to
        global settings.
        """
        global_key = "%s_%s" % (config_prefix, key)
        if key in kwds:
            return kwds.get(key)
        elif self.app_info and hasattr(self.app_info, global_key):
            return getattr(self.app_info, global_key)
        else:
            return default

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

    def __str__(self):
        return "%s[]" % self.__class__.__name__
