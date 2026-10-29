from dataclasses import dataclass
from typing import (
    Annotated,
    TYPE_CHECKING,
)
from urllib.parse import urlsplit

from pydantic import (
    Field,
    field_validator,
)

from galaxy.files import USER_FILE_SOURCES_SCHEME
from galaxy.files.models import FilesSourceRuntimeContext
from galaxy.files.uris import refuse_a_private_address
from galaxy.util.config_parsers import IpAllowedListEntryT
from galaxy.util.config_templates import TemplateExpansion
from ._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)

try:
    from webdav4.fsspec import WebdavFileSystem
except ImportError:
    WebdavFileSystem = None

if TYPE_CHECKING:
    import httpx

EXAMPLE_URL = "https://webdav.example.org"


@dataclass(frozen=True)
class RefusePrivateAddresses:
    """An httpx request hook; a dataclass, so its repr is stable and fsspec can still cache the filesystem."""

    trusted_host: str | None
    allowlist: tuple[IpAllowedListEntryT, ...]
    label: str

    def __call__(self, request: "httpx.Request") -> None:
        # servers like dCache redirect downloads to other hosts
        if request.url.host != self.trusted_host:
            refuse_a_private_address(str(request.url), list(self.allowlist), self.label, EXAMPLE_URL)


class WebDavFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    root: str | TemplateExpansion | None = None
    base_url: str | TemplateExpansion
    login: str | TemplateExpansion | None = None
    password: str | TemplateExpansion | None = None
    token: str | TemplateExpansion | None = None


class WebDavFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    root: str | None = None
    base_url: Annotated[
        str,
        Field(
            title="WebDAV base URL",
            description="The fully-qualified WebDAV endpoint URL used to access this file source.",
        ),
    ]
    login: str | None = None
    password: str | None = None
    token: Annotated[
        str | None,
        Field(
            title="Bearer token",
            description="Optional bearer token, used instead of login and password, for servers such as dCache.",
        ),
    ] = None

    @field_validator("token")
    @classmethod
    def strip_token(cls, value: str | None) -> str | None:
        return (value or "").strip() or None


class WebDavFilesSource(FsspecFilesSource[WebDavFileSourceTemplateConfiguration, WebDavFileSourceConfiguration]):
    plugin_type = "webdav"
    required_module = WebdavFileSystem
    required_package = "webdav4"

    template_config_class = WebDavFileSourceTemplateConfiguration
    resolved_config_class = WebDavFileSourceConfiguration

    @staticmethod
    def _webdav_endpoint(base_url: str, root: str | None) -> str:
        # WebDAV "root" is the service endpoint path (for example Nextcloud's
        # /remote.php/dav/files/user), not a directory prefix inside the file source.
        base_url = base_url.strip().rstrip("/")
        if not base_url:
            raise ValueError("base_url is required for WebDAV file source")
        root = root.strip().strip("/") if root else ""
        if root:
            return f"{base_url}/{root}"
        return base_url

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[WebDavFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ):
        if WebdavFileSystem is None:
            raise self.required_package_exception

        config = context.config
        endpoint = self._webdav_endpoint(config.base_url, config.root)
        auth = (config.login, config.password) if not config.token and (config.login or config.password) else None
        headers = {"Authorization": f"Bearer {config.token}"} if config.token else None
        # a server an admin configured is trusted; one a user typed into a template is checked like any other
        trusted_host = None if self.get_scheme() == USER_FILE_SOURCES_SCHEME else urlsplit(endpoint).hostname
        check = RefusePrivateAddresses(
            trusted_host, tuple(self._file_sources_config.fetch_url_allowlist or []), self.label
        )
        return WebdavFileSystem(
            endpoint,
            auth=auth,
            headers=headers,
            event_hooks={"request": [check]},
            # fsspec keeps every cached instance for the life of the process, one per token and thread
            skip_instance_cache=config.token is not None,
        )

    def _to_filesystem_path(self, path: str, config: WebDavFileSourceConfiguration) -> str:
        if path in ("", "/"):
            return ""
        return path.lstrip("/")

    def _adapt_entry_path(self, filesystem_path: str, config: WebDavFileSourceConfiguration) -> str:
        if not filesystem_path or filesystem_path == "/":
            return "/"
        return filesystem_path if filesystem_path.startswith("/") else f"/{filesystem_path}"


__all__ = ("WebDavFilesSource",)
