from . import ToolLocationResolver


class HttpToolResolver(ToolLocationResolver):
    scheme = "file"

    def get_tool_source_path(self, uri_like: str) -> str:
        assert uri_like.startswith("file://")
        return uri_like[len("file://") :]
