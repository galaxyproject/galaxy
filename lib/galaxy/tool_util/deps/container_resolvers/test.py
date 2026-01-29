from typing import (
    Container,
    Optional,
    TYPE_CHECKING,
)

from . import ContainerResolver

if TYPE_CHECKING:
    from ..dependencies import ToolInfo
    from ..requirements import ContainerDescription


class NullContainerResolver(ContainerResolver):
    """
    helper ContainerResolver that does not resolve ever

    for testing
    """

    resolver_type = "null"

    def resolve(
        self, enabled_container_types: Container[str], tool_info: "ToolInfo", **kwds
    ) -> Optional["ContainerDescription"]:
        return None


__all__ = ("NullContainerResolver",)
