from typing import (
    Annotated,
    Any,
    Optional,
    Union,
)

from pydantic import (
    Field,
    field_validator,
    model_validator,
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


def _normalize_root(root: Optional[str]) -> Optional[str]:
    if root is None:
        return None
    root = root.strip()
    if not root or root == "/":
        return None
    return f"/{root.strip('/')}"


def _normalize_base_url(base_url: Optional[str]) -> Optional[str]:
    if base_url is None:
        return None
    base_url = base_url.strip()
    if not base_url:
        return None
    return base_url.rstrip("/")


def _compose_base_url(url: Optional[str], root: Optional[str]) -> Optional[str]:
    # WebDAV "root" is the service endpoint path (for example Nextcloud's
    # /remote.php/dav/files/user), not a directory prefix inside the file source.
    if not url:
        return None
    url = url.rstrip("/")
    normalized_root = _normalize_root(root)
    if normalized_root:
        return f"{url}{normalized_root}"
    return url


class WebDavFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    url: Union[str, TemplateExpansion, None] = None
    root: Optional[Union[str, TemplateExpansion]] = None
    base_url: Union[str, TemplateExpansion, None] = None
    login: Optional[Union[str, TemplateExpansion]] = None
    password: Optional[Union[str, TemplateExpansion]] = None
    temp_path: Optional[Union[str, TemplateExpansion]] = None
    use_temp_files: Union[bool, TemplateExpansion] = True

    @model_validator(mode="before")
    @classmethod
    def normalize_endpoint(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        normalized["base_url"] = _normalize_base_url(
            normalized.get("base_url") or _compose_base_url(normalized.get("url"), normalized.get("root"))
        )
        return normalized


class WebDavFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    url: Optional[str] = None
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
    temp_path: Optional[str] = None
    use_temp_files: bool = True

    @model_validator(mode="before")
    @classmethod
    def normalize_endpoint(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        normalized["base_url"] = _normalize_base_url(
            normalized.get("base_url") or _compose_base_url(normalized.get("url"), normalized.get("root"))
        )
        return normalized

    @field_validator("base_url")
    @classmethod
    def validate_base_url_required(cls, v: str) -> str:
        if not v:
            raise ValueError("base_url is required for WebDAV file source")
        return v


class WebDavFilesSource(FsspecFilesSource[WebDavFileSourceTemplateConfiguration, WebDavFileSourceConfiguration]):
    plugin_type = "webdav"
    required_module = WebdavFileSystem
    required_package = "webdav4"

    template_config_class = WebDavFileSourceTemplateConfiguration
    resolved_config_class = WebDavFileSourceConfiguration

    def __init__(self, template_config: WebDavFileSourceTemplateConfiguration):
        defaults: dict[str, Any] = {}
        if (
            "use_temp_files" not in template_config.model_fields_set
            and template_config.file_sources_config.webdav_use_temp_files is not None
        ):
            defaults["use_temp_files"] = template_config.file_sources_config.webdav_use_temp_files
        if defaults:
            template_config = self._apply_defaults_to_template(defaults, template_config)
        super().__init__(template_config)

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[WebDavFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ):
        if WebdavFileSystem is None:
            raise self.required_package_exception

        config = context.config
        auth = (config.login, config.password) if config.login or config.password else None
        return WebdavFileSystem(config.base_url, auth=auth)

    def _to_filesystem_path(self, path: str, config: WebDavFileSourceConfiguration) -> str:
        if path in ("", "/"):
            return ""
        return path.lstrip("/")

    def _adapt_entry_path(self, filesystem_path: str, config: WebDavFileSourceConfiguration) -> str:
        if not filesystem_path or filesystem_path == "/":
            return "/"
        return filesystem_path if filesystem_path.startswith("/") else f"/{filesystem_path}"



__all__ = ("WebDavFilesSource",)
