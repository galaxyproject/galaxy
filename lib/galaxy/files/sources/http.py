import logging
import re
import urllib.request
from typing import (
    cast,
    Dict,
    List,
    Optional,
)

from typing_extensions import Unpack

from galaxy.files import OptionalUserContext
from galaxy.files.uris import validate_non_local
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    get_charset_from_http_headers,
    stream_to_open_named_file,
)
from galaxy.util.config_parsers import IpAllowedListEntryT
from . import (
    BaseFilesSource,
    FilesSourceOptions,
    FilesSourceProperties,
    PluginKind,
)

log = logging.getLogger(__name__)


class HTTPFilesSourceProperties(FilesSourceProperties, total=False):
    url_regex: str
    http_headers: Dict[str, str]
    fetch_url_allowlist: List[IpAllowedListEntryT]


class HTTPFilesSource(BaseFilesSource):
    plugin_type = "http"
    plugin_kind = PluginKind.stock

    def __init__(self, **kwd: Unpack[FilesSourceProperties]):
        kwds: FilesSourceProperties = dict(
            id="_http",
            label="HTTP File",
            doc="Default HTTP file handler",
            writable=False,
        )
        kwds.update(kwd)
        props: HTTPFilesSourceProperties = cast(HTTPFilesSourceProperties, self._parse_common_config_opts(kwds))
        self._url_regex_str = props.pop("url_regex", r"^https?://|^ftp://")
        assert self._url_regex_str
        self._url_regex = re.compile(self._url_regex_str)
        self._props = props

    @property
    def _allowlist(self):
        return self._file_sources_config.fetch_url_allowlist

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        props = self._serialization_props(user_context)
        extra_props: HTTPFilesSourceProperties = cast(HTTPFilesSourceProperties, opts.extra_props or {} if opts else {})
        headers = props.pop("http_headers", {}) or {}
        headers.update(extra_props.get("http_headers") or {})
        req = urllib.request.Request(source_path, headers=headers)

        with urllib.request.urlopen(req, timeout=DEFAULT_SOCKET_TIMEOUT) as page:
            # Verify url post-redirects is still allowlisted
            validate_non_local(page.geturl(), self._allowlist or extra_props.get("fetch_url_allowlist") or [])
            f = open(native_path, "wb")  # fd will be .close()ed in stream_to_open_named_file
            return stream_to_open_named_file(
                page, f.fileno(), native_path, source_encoding=get_charset_from_http_headers(page.headers)
            )

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        raise NotImplementedError()

    def _serialization_props(self, user_context: OptionalUserContext = None) -> HTTPFilesSourceProperties:
        effective_props = {}
        for key, val in self._props.items():
            effective_props[key] = self._evaluate_prop(val, user_context=user_context)
        effective_props["url_regex"] = self._url_regex_str
        return cast(HTTPFilesSourceProperties, effective_props)

    def score_url_match(self, url: str):
        if match := self._url_regex.match(url):
            return match.span()[1]
        else:
            return 0


__all__ = ("HTTPFilesSource",)
