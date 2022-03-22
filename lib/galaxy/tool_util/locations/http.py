from galaxy.util import download_to_file
from ..locations import ToolLocationResolver


class HttpToolResolver(ToolLocationResolver):

    scheme = "http"

    def __init__(self, **kwds):
        pass

    def get_tool_source_path(self, uri_like):
        tmp_path = self._temp_path(uri_like)
        download_to_file(uri_like, tmp_path)
        return tmp_path


class HttpsToolResolver(HttpToolResolver):

    scheme = "https"


__all__ = ("HttpToolResolver", "HttpsToolResolver")
