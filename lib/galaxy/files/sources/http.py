import logging
import re
import urllib.request
from typing import Union
from urllib.parse import (
    quote,
    urlsplit,
)

from requests.exceptions import InvalidURL
from requests.utils import unquote_unreserved

from galaxy.files.models import (
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
    FilesSourceRuntimeContext,
)
from galaxy.files.uris import validate_non_local
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    get_charset_from_http_headers,
    stream_to_path,
)
from galaxy.util.config_parsers import IpAllowedListEntryT
from galaxy.util.config_templates import TemplateExpansion
from . import (
    BaseFilesSource,
    PluginKind,
)

log = logging.getLogger(__name__)

# ASCII control characters, space, and DEL must be percent-encoded in a URL;
# same character set http.client refuses in a request line.
_DISALLOWED_URL_CHARACTERS = re.compile(r"[\x00-\x20\x7f]")


def _requote_http_url(url: str) -> str:
    # Percent-encode characters such as <, > and " the way requests does, leaving scheme and host untouched.
    parts = urlsplit(url)
    authority_end = len(parts.scheme) + len("://") + len(parts.netloc)
    try:
        path = unquote_unreserved(url[authority_end:])
    except InvalidURL:
        # requote_uri's fallback would double-encode valid escapes; send the URL as given.
        return url
    return url[:authority_end] + quote(path, safe="!#$%&'()*+,/:;=?@[]~")


class HTTPFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    # `url_regex` is not templated because it needs to be set at initialization with no RuntimeContext available.
    url_regex: str = r"^https?://|^ftp://"
    http_headers: Union[dict[str, str], TemplateExpansion] = {}
    fetch_url_allowlist: Union[list[IpAllowedListEntryT], TemplateExpansion] = []


class HTTPFileSourceConfiguration(BaseFileSourceConfiguration):
    url_regex: str = r"^https?://|^ftp://"
    http_headers: dict[str, str] = {}
    fetch_url_allowlist: list[IpAllowedListEntryT] = []


class HTTPFilesSource(BaseFilesSource[HTTPFileSourceTemplateConfiguration, HTTPFileSourceConfiguration]):
    plugin_type = "http"
    plugin_kind = PluginKind.stock

    template_config_class = HTTPFileSourceTemplateConfiguration
    resolved_config_class = HTTPFileSourceConfiguration

    def __init__(self, template_config: HTTPFileSourceTemplateConfiguration):
        defaults = dict(
            id="_http",
            label="HTTP File",
            doc="Default HTTP file handler",
            writable=False,
        )
        template_config = self._apply_defaults_to_template(defaults, template_config)
        super().__init__(template_config)
        assert self.template_config.url_regex, "HTTPFilesSource requires a url_regex to be set in the configuration"
        self._compiled_url_regex = re.compile(self.template_config.url_regex)

    @property
    def _allowlist(self):
        return self._file_sources_config.fetch_url_allowlist

    def _realize_to(
        self, source_path: str, native_path: str, context: FilesSourceRuntimeContext[HTTPFileSourceConfiguration]
    ):
        config = context.config
        request_url = source_path
        if urlsplit(source_path).scheme.lower() in ("http", "https"):
            if _DISALLOWED_URL_CHARACTERS.search(source_path):
                raise ValueError(
                    f"URL contains unencoded characters (e.g. spaces): {source_path}. "
                    "The URL source should properly percent-encode the path."
                )
            request_url = _requote_http_url(source_path)
        req = urllib.request.Request(request_url, headers=config.http_headers)
        page = urllib.request.urlopen(req, timeout=DEFAULT_SOCKET_TIMEOUT)
        with page:
            # Verify url post-redirects is still allowlisted
            validate_non_local(page.geturl(), self._allowlist or config.fetch_url_allowlist)
            return stream_to_path(page, native_path, source_encoding=get_charset_from_http_headers(page.headers))

    def _write_from(
        self, target_path: str, native_path: str, context: FilesSourceRuntimeContext[HTTPFileSourceConfiguration]
    ):
        raise NotImplementedError()

    def score_url_match(self, url: str):
        if match := self._compiled_url_regex.match(url):
            return match.span()[1]
        else:
            return 0


__all__ = ("HTTPFilesSource",)
