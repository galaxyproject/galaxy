import logging
import os
import urllib.parse

import requests
import yaml

from galaxy.exceptions import MessageException
from galaxy.util import (
    asbool,
    DEFAULT_SOCKET_TIMEOUT,
)
from galaxy.util.search import parse_filters

log = logging.getLogger(__name__)

# Make configurable via YAML,JSON
DEFAULT_TRS_SERVERS = [
    {
        "id": "dockstore",
        "api_url": "https://dockstore.org/api",
        "link_url": "https://dockstore.org",
        "label": "Dockstore",
        "doc": "Dockstore is an open platform used by the GA4GH for sharing Docker-based tools and workflows.",
    },
]
GA4GH_GALAXY_DESCRIPTOR = "GALAXY"


def parse_search_kwds(search_query):
    filters = {
        "organization": "organization",
        "o": "organization",
        "name": "name",
        "n": "name",
    }
    keyed_terms, description_term = parse_filters(search_query, filters)
    query_kwd = {
        "toolClass": "Workflow",
        "descriptorType": "GALAXY",
    }
    if description_term and description_term.strip():
        query_kwd["description"] = (description_term,)

    if keyed_terms is not None:
        for (key, value, _) in keyed_terms:
            query_kwd[key] = value
    return query_kwd


class TrsProxy:
    def __init__(self, config=None):
        config_file = getattr(config, "trs_servers_config_file", None)
        if config_file and os.path.exists(config_file):
            with open(config_file) as f:
                server_list = yaml.safe_load(f)
        else:
            server_list = DEFAULT_TRS_SERVERS
        self._server_list = server_list if server_list else []
        self._server_dict = {t["id"]: t for t in self._server_list}

    def get_servers(self):
        return self._server_list

    def get_tools(self, trs_server, **kwd):
        query_kwd = {}
        for key in ["toolClass", "descriptorType", "description", "name", "organization"]:
            value = kwd.pop(key, None)
            if value is not None:
                query_kwd[key] = value

        trs_api_url = self._get_api_endpoint(trs_server, **kwd)
        return self._get(trs_api_url, params=query_kwd)

    def get_tool(self, trs_server, tool_id, **kwd):
        trs_api_url = self._get_tool_api_endpoint(trs_server, tool_id, **kwd)
        return self._get(trs_api_url)

    def get_versions(self, trs_server, tool_id, **kwd):
        trs_api_url = f"{self._get_tool_api_endpoint(trs_server, tool_id, **kwd)}/versions"
        return self._get(trs_api_url)

    def get_version(self, trs_server, tool_id, version_id, **kwd):
        trs_api_url = f"{self._get_tool_api_endpoint(trs_server, tool_id, **kwd)}/versions/{version_id}"
        return self._get(trs_api_url)

    def get_version_descriptor(self, trs_server, tool_id, version_id, **kwd):
        trs_api_url = f"{self._get_tool_api_endpoint(trs_server, tool_id, **kwd)}/versions/{version_id}/{GA4GH_GALAXY_DESCRIPTOR}/descriptor"
        return self._get(trs_api_url)["content"]

    def _quote(self, tool_id, **kwd):
        if asbool(kwd.get("tool_id_b64_encoded", False)):
            import base64

            tool_id = base64.b64decode(tool_id)
        tool_id = urllib.parse.quote_plus(tool_id)
        return tool_id

    def _get(self, url, params=None):
        response = requests.get(url, params=params, timeout=DEFAULT_SOCKET_TIMEOUT)
        if response.ok:
            return response.json()
        else:
            code = response.status_code
            message = response.text
            try:
                trs_error_dict = response.json()
                code = int(trs_error_dict["code"])
                message = trs_error_dict["message"]
            except Exception:
                pass
            raise MessageException.from_code(code, message)

    def _get_api_endpoint(self, trs_server, **kwd):
        trs_url = self._server_dict[trs_server]["api_url"]
        trs_api_endpoint = f"{trs_url}/ga4gh/trs/v2/tools"
        return trs_api_endpoint

    def _get_tool_api_endpoint(self, trs_server, tool_id, **kwd):
        tool_id = self._quote(tool_id, **kwd)
        trs_api_url = f"{self._get_api_endpoint(trs_server, **kwd)}/{tool_id}"
        return trs_api_url
