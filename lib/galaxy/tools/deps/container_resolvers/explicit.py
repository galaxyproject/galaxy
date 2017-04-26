"""This module describes the :class:`ExplicitContainerResolver` ContainerResolver plugin."""
import logging

from ..container_resolvers import (
    ContainerResolver,
)

log = logging.getLogger(__name__)


class ExplicitContainerResolver(ContainerResolver):
    """Find explicit containers referenced in the tool description (e.g. tool XML file) if present."""

    resolver_type = "explicit"

    def resolve(self, enabled_container_types, tool_info):
        """Find a container explicitly mentioned in tool description.

        This ignores the tool requirements and assumes the tool author crafted
        a correct container.
        """
        for container_description in tool_info.container_descriptions:
            if self._container_type_enabled(container_description, enabled_container_types):
                return container_description

        return None
