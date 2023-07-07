import ssl
import urllib.request
from typing import (
    cast,
    Optional,
)
from urllib.parse import urljoin

import requests
from typing_extensions import Unpack

from galaxy.files.sources import (
    BaseFilesSource,
    FilesSourceOptions,
    FilesSourceProperties,
)
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    get_charset_from_http_headers,
    stream_to_open_named_file,
)

# TODO: Remove this block. Ignoring SSL errors for testing purposes.
VERIFY = False
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE


class InvenioFilesSourceProperties(FilesSourceProperties):
    url: str


class InvenioFilesSource(BaseFilesSource):
    """A files source for Invenio turn-key research data management repository."""

    plugin_type = "inveniordm"

    def __init__(self, **kwd: Unpack[InvenioFilesSourceProperties]):
        props = self._parse_common_config_opts(kwd)
        base_url = props.get("url", None)
        if not base_url:
            raise Exception("InvenioFilesSource requires a url")
        self._invenio_url = base_url
        self._props = props

    def _list(self, path="/", recursive=True, user_context=None, opts: Optional[FilesSourceOptions] = None):
        is_listing_records = path == "/"
        if is_listing_records:
            # TODO: This is limited to 25 records by default. We should add pagination support.
            request_url = urljoin(self._invenio_url, "api/records")
        else:
            # listing a record's files
            request_url = urljoin(self._invenio_url, f"{path}/files")

        rval = []
        headers = self._get_request_headers(user_context)
        response = requests.get(request_url, headers=headers, verify=VERIFY)
        if response.status_code == 200:
            response_json = response.json()
            if is_listing_records:
                rval = self._get_records_from_response(path, response_json)
            else:
                rval = self._get_record_files_from_response(path, response_json)
        else:
            raise Exception(f"Request to {request_url} failed with status code {response.status_code}")
        return rval

    def _get_request_headers(self, user_context):
        preferences = user_context.preferences if user_context else None
        token = preferences.get(f"{self.id}|token", None) if preferences else None
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return headers

    def _get_records_from_response(self, path: str, response: dict):
        records = response["hits"]["hits"]
        rval = []
        for record in records:
            uri = self._to_plugin_uri(record["links"]["self"])
            rval.append(
                {
                    "class": "Directory",
                    "name": record["metadata"]["title"],
                    "ctime": record["created"],
                    "uri": uri,
                    "path": path,
                }
            )

        return rval

    def _get_record_files_from_response(self, path: str, response: dict):
        files_enabled = response.get("enabled", False)
        if not files_enabled:
            return []
        entries = response["entries"]
        rval = []
        for entry in entries:
            if entry.get("status") == "completed":
                uri = self._to_plugin_uri(entry["links"]["content"])
                rval.append(
                    {
                        "class": "File",
                        "name": entry["key"],
                        "size": entry["size"],
                        "ctime": entry["created"],
                        "uri": uri,
                        "path": path,
                    }
                )
        return rval

    def _to_plugin_uri(self, uri: str) -> str:
        return uri.replace(self._invenio_url, self.get_uri_root())

    def _realize_to(
        self, source_path: str, native_path: str, user_context=None, opts: Optional[FilesSourceOptions] = None
    ):
        remote_path = urljoin(self._invenio_url, source_path)
        # TODO: user_context is always None here when called from a data fetch.
        # This prevents downloading files that require authentication even if the user provided a token.
        headers = self._get_request_headers(user_context)
        req = urllib.request.Request(remote_path, headers=headers)
        with urllib.request.urlopen(req, timeout=DEFAULT_SOCKET_TIMEOUT, context=SSL_CONTEXT) as page:
            f = open(native_path, "wb")
            return stream_to_open_named_file(
                page, f.fileno(), native_path, source_encoding=get_charset_from_http_headers(page.headers)
            )

    def _write_from(
        self, target_path: str, native_path: str, user_context=None, opts: Optional[FilesSourceOptions] = None
    ):
        raise NotImplementedError()

    def _serialization_props(self, user_context=None) -> InvenioFilesSourceProperties:
        effective_props = {}
        for key, val in self._props.items():
            effective_props[key] = self._evaluate_prop(val, user_context=user_context)
        effective_props["url"] = self._invenio_url
        return cast(InvenioFilesSourceProperties, effective_props)


__all__ = ("InvenioFilesSource",)
