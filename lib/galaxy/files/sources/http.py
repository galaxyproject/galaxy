import logging
import re
import urllib.request

from galaxy.files.uris import validate_non_local
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    get_charset_from_http_headers,
    stream_to_open_named_file,
)
from galaxy.util.config_parsers import IpAllowedListEntryT
from . import (
    BaseFilesSource,
    FilesSourceProperties,
    PluginKind,
)

log = logging.getLogger(__name__)


class HTTPFileSourceConfiguration(FilesSourceProperties):
    url_regex: str = r"^https?://|^ftp://"
    http_headers: dict[str, str] = {}
    fetch_url_allowlist: list[IpAllowedListEntryT] = []


class HTTPFilesSource(BaseFilesSource):
    plugin_type = "http"
    plugin_kind = PluginKind.stock
    config_class = HTTPFileSourceConfiguration
    config: HTTPFileSourceConfiguration

    def __init__(self, config: HTTPFileSourceConfiguration):
        super().__init__(config)
        overrides = dict(
            id="_http",
            label="HTTP File",
            doc="Default HTTP file handler",
            writable=False,
        )
        self.config = self.config.model_copy(update=overrides)

        assert self.config.url_regex, "HTTPFilesSource requires a url_regex to be set in the configuration"
        self._compiled_url_regex = re.compile(self.config.url_regex)

    @property
    def _allowlist(self):
        return self._file_sources_config.fetch_url_allowlist

    def _realize_to(self, source_path: str, native_path: str):
        req = urllib.request.Request(source_path, headers=self.config.http_headers)

        with urllib.request.urlopen(req, timeout=DEFAULT_SOCKET_TIMEOUT) as page:
            # Verify url post-redirects is still allowlisted
            validate_non_local(page.geturl(), self._allowlist or self.config.fetch_url_allowlist)
            f = open(native_path, "wb")  # fd will be .close()ed in stream_to_open_named_file
            return stream_to_open_named_file(
                page, f.fileno(), native_path, source_encoding=get_charset_from_http_headers(page.headers)
            )

    def _write_from(self, target_path: str, native_path: str):
        raise NotImplementedError()

    def score_url_match(self, url: str):
        if match := self._compiled_url_regex.match(url):
            return match.span()[1]
        else:
            return 0


__all__ = ("HTTPFilesSource",)
