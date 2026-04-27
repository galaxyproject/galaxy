from typing import (
    Annotated,
    Optional,
    Union,
)

from pydantic import (
    Field,
)

from galaxy.files.models import FilesSourceRuntimeContext
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


class WebDavFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    root: Optional[Union[str, TemplateExpansion]] = None
    base_url: Union[str, TemplateExpansion]
    login: Optional[Union[str, TemplateExpansion]] = None
    password: Optional[Union[str, TemplateExpansion]] = None


class WebDavFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    root: Optional[str] = None
    base_url: Annotated[
        str,
        Field(
            title="WebDAV base URL",
            description="The fully-qualified WebDAV endpoint URL used to access this file source.",
        ),
    ]
    login: Optional[str] = None
    password: Optional[str] = None


class WebDavFilesSource(FsspecFilesSource[WebDavFileSourceTemplateConfiguration, WebDavFileSourceConfiguration]):
    plugin_type = "webdav"
    required_module = WebdavFileSystem
    required_package = "webdav4"

    template_config_class = WebDavFileSourceTemplateConfiguration
    resolved_config_class = WebDavFileSourceConfiguration

    @staticmethod
    def _webdav_endpoint(base_url: str, root: Optional[str]) -> str:
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
        auth = (config.login, config.password) if config.login or config.password else None
        return WebdavFileSystem(self._webdav_endpoint(config.base_url, config.root), auth=auth)

    def _to_filesystem_path(self, path: str, config: WebDavFileSourceConfiguration) -> str:
        if path in ("", "/"):
            return ""
        return path.lstrip("/")

    def _adapt_entry_path(self, filesystem_path: str, config: WebDavFileSourceConfiguration) -> str:
        if not filesystem_path or filesystem_path == "/":
            return "/"
        return filesystem_path if filesystem_path.startswith("/") else f"/{filesystem_path}"


__all__ = ("WebDavFilesSource",)
