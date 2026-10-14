import posixpath
import shutil

from fsspec import AbstractFileSystem
from pydantic import field_validator

from galaxy.exceptions import MessageException
from galaxy.files.models import FilesSourceRuntimeContext
from galaxy.files.sources._defaults import DEFAULT_SCHEME
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
    normalize_rooted_relative_path,
)
from galaxy.util.config_templates import TemplateExpansion

try:
    import fsspec_xrootd

    XRootDFileSystem: type[AbstractFileSystem] | None = fsspec_xrootd.XRootDFileSystem
except ImportError:
    XRootDFileSystem = None


def _normalize_root(value: str) -> str:
    root = value.strip()
    if not root or not root.startswith("/"):
        raise ValueError("XRootD root must be an absolute directory path.")
    return "/" + posixpath.normpath(root).lstrip("/")


class XRootDFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    root: str | TemplateExpansion
    hostid: str | TemplateExpansion
    timeout: int | TemplateExpansion = 30

    @field_validator("root")
    @classmethod
    def validate_root(cls, value: str) -> str:
        # Cheetah expressions must be validated after expansion, at runtime.
        return value if "$" in value else _normalize_root(value)


class XRootDFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    root: str
    hostid: str
    timeout: int = 30

    @field_validator("root")
    @classmethod
    def validate_root(cls, value: str) -> str:
        return _normalize_root(value)


class XRootDFilesSource(FsspecFilesSource[XRootDFileSourceTemplateConfiguration, XRootDFileSourceConfiguration]):
    plugin_type = "xrootd"
    required_module = XRootDFileSystem
    required_package = "fsspec-xrootd"

    template_config_class = XRootDFileSourceTemplateConfiguration
    resolved_config_class = XRootDFileSourceConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[XRootDFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ) -> AbstractFileSystem:
        if XRootDFileSystem is None:
            raise self.required_package_exception

        return XRootDFileSystem(
            hostid=context.config.hostid,
            timeout=context.config.timeout,
            asynchronous=False,
            **cache_options,
        )

    def _to_filesystem_path(self, path: str, config: XRootDFileSourceConfiguration) -> str:
        relative_path = normalize_rooted_relative_path(path, "XRootD")
        return f"{config.root.rstrip('/')}/{relative_path}" if relative_path else config.root

    def _adapt_entry_path(self, filesystem_path: str, config: XRootDFileSourceConfiguration) -> str:
        normalized_path = "/" + filesystem_path.lstrip("/")
        if normalized_path == config.root:
            return "/"
        root_prefix = config.root.rstrip("/") + "/"
        if not normalized_path.startswith(root_prefix):
            raise MessageException(f"Unexpected XRootD listing entry outside configured root: {filesystem_path!r}")
        relative_path = normalize_rooted_relative_path(normalized_path[len(root_prefix) :], "XRootD")
        return f"/{relative_path}"

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[XRootDFileSourceConfiguration],
    ) -> None:
        target_path = self._to_filesystem_path(target_path, context.config)
        cache_options = self._get_cache_options(context.config)
        fs = self._open_fs(context, cache_options)
        # fsspec-xrootd supports file writes but does not implement put_file().
        # Unlike put_file(), parent directories are not created; uploads target existing directories.
        with open(native_path, "rb") as source:
            with fs.open(target_path, "wb") as destination:
                shutil.copyfileobj(source, destination, length=1024 * 1024)

    def get_scheme(self) -> str:
        return self.scheme if self.scheme and self.scheme != DEFAULT_SCHEME else "xrootd"


__all__ = ("XRootDFilesSource",)
