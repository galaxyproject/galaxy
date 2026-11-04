import logging
import os
import re
import urllib.parse
from typing import Any

import yaml

from galaxy.config import Configuration
from galaxy.exceptions import (
    GatewayTimeoutException,
    MessageException,
    RequestParameterInvalidException,
    UpstreamProxyError,
)
from galaxy.files.uris import validate_non_local
from galaxy.util import (
    asbool,
    requests,
)
from galaxy.util.config_parsers import IpAllowedListEntryT
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
# (connect, read) timeout in seconds for requests to TRS servers. Galaxy proxies these requests while
# the user waits in the import form, so give up on an unresponsive server and report the failure.
# These limit each connection attempt and each wait for data from the server, not the whole request.
TRS_REQUEST_TIMEOUT = (10, 30)
TRS_URL_REGEX = (
    r"(?P<trs_base_url>https?:\/\/.+)\/ga4gh\/trs\/v2\/tools\/(?P<tool_id>.+)\/versions\/(?P<version_id>[^\/]+).*"
)
TRS_VERSION_NUMBER_REGEX = re.compile(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", re.ASCII)
TRS_RELEASE_NAME_REGEX = re.compile(r"v?\d+(?:\.\d+){0,2}", re.ASCII)


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
        for key, value, _ in keyed_terms:
            query_kwd[key] = value
    return query_kwd


def parse_trs_url(url: str) -> dict[str, str] | None:
    """Split a TRS version URL into trs_base_url, tool_id and version_id, both unquoted."""
    if matches := re.match(TRS_URL_REGEX, url):
        match_dict = matches.groupdict()
        match_dict["tool_id"] = urllib.parse.unquote(match_dict["tool_id"])
        match_dict["version_id"] = urllib.parse.unquote(match_dict["version_id"])
        return match_dict
    return None


def parse_trs_version(name: str) -> tuple[int, int, int] | None:
    """Numeric parts of a TRS version name like ``v1.2.3``, or None for a name without a number, e.g. a branch.

    Matches the client's ``parseTrsVersion``, so the server and the client order versions the same way.
    """
    if match := TRS_VERSION_NUMBER_REGEX.search(name):
        major, minor, patch = match.groups()
        return int(major), int(minor or 0), int(patch or 0)
    return None


def trs_version_id(version: dict[str, Any]) -> str:
    """The id that addresses a TRS ToolVersion in a TRS version URL.

    Dockstore version ids repeat the tool id (``#workflow/...:v0.1``), its URLs use the version name.
    """
    version_id: str = version["id"]
    name: str | None = version.get("name")
    if name and f":{name}" in version_id:
        return name
    return version_id


def sort_trs_versions(versions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Numbered versions first, newest first, then the others (e.g. branches) by name, descending."""
    numbered = [v for v in versions if parse_trs_version(v.get("name") or "")]
    others = [v for v in versions if not parse_trs_version(v.get("name") or "")]
    numbered.sort(key=lambda v: parse_trs_version(v["name"]) or (0, 0, 0), reverse=True)
    others.sort(key=lambda v: (v.get("name") or "").casefold(), reverse=True)
    return numbered + others


def _parse_trs_release(name: str) -> tuple[int, int, int] | None:
    return parse_trs_version(name) if TRS_RELEASE_NAME_REGEX.fullmatch(name) else None


def trs_upgrade_version_id(sorted_versions: list[dict[str, Any]], current_trs_version_id: str) -> str | None:
    """The newest release in ``sort_trs_versions`` output, if it is newer than the current release.

    Releases are named like ``v1.2.3``. A branch or pre-release is never chosen, and a workflow imported from one stays on it.
    """
    current_name = next(
        (v.get("name") or "" for v in sorted_versions if trs_version_id(v) == current_trs_version_id),
        current_trs_version_id,
    )
    current = _parse_trs_release(current_name)
    if current is None:
        return None
    for version in sorted_versions:
        newest = _parse_trs_release(version.get("name") or "")
        if newest is not None:
            return trs_version_id(version) if newest > current else None
    return None


class TrsProxy:
    def __init__(self, config: Configuration):
        config_file = config.trs_servers_config_file
        if config_file and os.path.exists(config_file):
            with open(config_file) as f:
                server_list = yaml.safe_load(f)
        else:
            server_list = DEFAULT_TRS_SERVERS
        self._server_list = server_list if server_list else []
        self._server_dict = {t["id"]: t for t in self._server_list}
        self.fetch_url_allowlist_ips = config.fetch_url_allowlist_ips

    def get_servers(self):
        return self._server_list

    def get_server(self, trs_server):
        try:
            trs_url = self._server_dict[trs_server]["api_url"]
        except KeyError:
            raise RequestParameterInvalidException(f"Unknown TRS server '{trs_server}'.")
        return TrsServer(trs_url)

    def server_from_url(self, trs_url):
        return TrsServer(trs_url)

    def get_trs_id_and_version_from_trs_url(self, trs_url):
        parts = self.match_url(trs_url, self.fetch_url_allowlist_ips)
        if parts:
            return self.server_from_url(parts["trs_base_url"]), parts["tool_id"], parts["version_id"]
        raise RequestParameterInvalidException(f"Invalid TRS URL {trs_url}.")

    def get_version_from_trs_url(self, trs_url):
        server, trs_tool_id, trs_version_id = self.get_trs_id_and_version_from_trs_url(trs_url=trs_url)
        return server.get_version_descriptor(trs_tool_id, trs_version_id)

    def match_url(self, url, ip_allowlist: list[IpAllowedListEntryT]):
        if url.lstrip().startswith("file://"):
            # requests doesn't know what to do with file:// anyway, but just in case we swap
            # out the implementation
            raise RequestParameterInvalidException(f"Invalid TRS URL {url}")
        validate_non_local(url, ip_allowlist=ip_allowlist or [])
        return self._match_url(url)

    def _match_url(self, url):
        return parse_trs_url(url)


class TrsServer:
    def __init__(self, trs_url):
        self._trs_url = trs_url

    def get_tools(self, **kwd):
        query_kwd = {}
        for key in ["toolClass", "descriptorType", "description", "name", "organization"]:
            value = kwd.pop(key, None)
            if value is not None:
                query_kwd[key] = value

        trs_api_url = self._get_api_endpoint(**kwd)
        return self._get(trs_api_url, params=query_kwd)

    def get_tool(self, tool_id, **kwd):
        trs_api_url = self._get_tool_api_endpoint(tool_id, **kwd)
        return self._get(trs_api_url)

    def get_versions(self, tool_id, **kwd):
        trs_api_url = f"{self._get_tool_api_endpoint(tool_id, **kwd)}/versions"
        return self._get(trs_api_url)

    def get_sorted_versions(self, tool_id, **kwd) -> list[dict[str, Any]]:
        versions = self.get_versions(tool_id, **kwd)
        if not isinstance(versions, list) or not all(isinstance(v, dict) and v.get("id") for v in versions):
            raise UpstreamProxyError(f"TRS server {self._trs_url} sent an invalid version list for {tool_id}.")
        return sort_trs_versions(versions)

    def get_version(self, tool_id, version_id, **kwd):
        return self._get(self._get_version_api_endpoint(tool_id, version_id, **kwd))

    def get_version_descriptor(self, tool_id, version_id, **kwd):
        trs_api_url = (
            f"{self._get_version_api_endpoint(tool_id, version_id, **kwd)}/{GA4GH_GALAXY_DESCRIPTOR}/descriptor"
        )
        return self._get(trs_api_url)["content"]

    def get_trs_url(self, tool_id: str, version_id: str):
        return self._get_version_api_endpoint(tool_id, version_id)

    def _quote(self, tool_id, **kwd):
        if asbool(kwd.get("tool_id_b64_encoded", False)):
            import base64

            tool_id = base64.b64decode(tool_id)
        tool_id = urllib.parse.quote_plus(tool_id)
        return tool_id

    def _get(self, url, params=None):
        try:
            response = requests.get(url, params=params, timeout=TRS_REQUEST_TIMEOUT)
        except requests.exceptions.Timeout as e:
            log.warning("Request to TRS server %s timed out: %s", self._trs_url, e)
            raise GatewayTimeoutException(f"TRS server {self._trs_url} did not respond in time.") from e
        except requests.exceptions.ConnectionError as e:
            log.warning("Request to TRS server %s failed: %s", self._trs_url, e)
            raise UpstreamProxyError(f"TRS server {self._trs_url} could not be reached.") from e
        if response.ok:
            try:
                return response.json()
            except ValueError as e:
                raise UpstreamProxyError(f"TRS server {self._trs_url} responded with a body that is not JSON.") from e
        try:
            trs_error_dict = response.json()
            code = int(trs_error_dict["code"])
            message = trs_error_dict["message"]
        except Exception:
            # Not a TRS error document, e.g. an HTML error page from a proxy or CDN in front of the server.
            code = response.status_code
            message = f"TRS server {self._trs_url} responded with HTTP {code}."
        raise MessageException.from_code(code, message)

    def _get_api_endpoint(self, **kwd):
        trs_url = self._trs_url
        trs_api_endpoint = f"{trs_url}/ga4gh/trs/v2/tools"
        return trs_api_endpoint

    def _get_tool_api_endpoint(self, tool_id, **kwd):
        tool_id = self._quote(tool_id, **kwd)
        trs_api_url = f"{self._get_api_endpoint(**kwd)}/{tool_id}"
        return trs_api_url

    def _get_version_api_endpoint(self, tool_id, version_id, **kwd):
        # Version ids can be branch names, which may contain "/".
        return f"{self._get_tool_api_endpoint(tool_id, **kwd)}/versions/{urllib.parse.quote(version_id, safe='')}"
