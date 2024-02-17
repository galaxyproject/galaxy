from typing import (
    Dict,
    Type,
    TYPE_CHECKING,
)

from galaxy.util import plugin_config

if TYPE_CHECKING:
    from galaxy.tool_util.locations import ToolLocationResolver


class ToolLocationFetcher:
    def __init__(self):
        self.resolver_classes = self.__resolvers_dict()

    def __resolvers_dict(self) -> Dict[str, Type["ToolLocationResolver"]]:
        import galaxy.tool_util.locations

        return plugin_config.plugins_dict(galaxy.tool_util.locations, "scheme")

    def to_tool_path(self, path_or_uri_like: str, **kwds) -> str:
        if "://" not in path_or_uri_like:
            path = path_or_uri_like
        else:
            uri_like = path_or_uri_like
            if ":" not in path_or_uri_like:
                raise Exception("Invalid URI passed to get_tool_source")
            scheme = uri_like.split(":", 2)[0]
            if scheme not in self.resolver_classes:
                raise Exception(f"Unknown tool scheme [{scheme}] for URI [{uri_like}]")
            path = self.resolver_classes[scheme]().get_tool_source_path(uri_like)

        return path
