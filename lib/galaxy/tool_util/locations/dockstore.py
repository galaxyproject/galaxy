from urllib.parse import quote

import requests
import yaml

from galaxy.util import DEFAULT_SOCKET_TIMEOUT
from ..locations import (
    ToolLocationResolver,
)


class DockStoreResolver(ToolLocationResolver):

    scheme = "dockstore"

    def get_tool_source_path(self, uri_like):
        assert uri_like.startswith("dockstore://")
        tool_id = uri_like[len("dockstore://"):]
        if ":" in tool_id:
            tool_id, version = tool_id.split(":", 1)
        else:
            tool_id, version = tool_id, "latest"
        tmp_path = self._temp_path(f"{uri_like}.cwl")
        cwl_str = _Ga4ghToolClient().get_tool_cwl(tool_id, version=version, as_string=True)
        with open(tmp_path, "wb") as f:
            f.write(cwl_str)
        return tmp_path


class _Ga4ghToolClient:

    def __init__(self, base_url="https://www.dockstore.org:8443/api"):
        self.base_url = base_url

    def get_tools(self):
        return self._requests.get(f"{self.base_url}/ga4gh/v1/tools", timeout=DEFAULT_SOCKET_TIMEOUT)

    def get_tool(self, tool_id):
        url = f"{self.base_url}/ga4gh/v1/tools/{quote(tool_id, safe='')}"
        return self._requests.get(url, timeout=DEFAULT_SOCKET_TIMEOUT)

    def get_tool_version(self, tool_id, version="latest"):
        url = f"{self.base_url}/ga4gh/v1/tools/{quote(tool_id, safe='')}/versions/{version}"
        return self._requests.get(url, timeout=DEFAULT_SOCKET_TIMEOUT)

    def get_tool_descriptor(self, tool_id, version="latest", tool_type="CWL"):
        url = f"{self.base_url}/ga4gh/v1/tools/{quote(tool_id, safe='')}/versions/{version}/{tool_type}/descriptor"
        return self._requests.get(url, timeout=DEFAULT_SOCKET_TIMEOUT)

    def get_tool_cwl(self, tool_id, version="latest", as_string=False):
        tool_type = "CWL"
        url = f"{self.base_url}/ga4gh/v1/tools/{quote(tool_id, safe='')}/versions/{version}/{tool_type}/descriptor"
        descriptor_response = self._requests.get(url, timeout=DEFAULT_SOCKET_TIMEOUT)
        descriptor_str = descriptor_response.json()["descriptor"]
        if as_string:
            return descriptor_str
        else:
            return yaml.safe_load(descriptor_str)

    @property
    def _requests(self):
        if requests is None:
            raise Exception("requests Python library needs to be installed use GA4GH APIs")
        return requests


__all__ = ("DockStoreResolver",)
