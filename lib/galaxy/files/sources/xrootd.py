import posixpath
from typing import Literal

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
)
from galaxy.util.config_templates import TemplateExpansion

try:
    from fsspec_xrootd import XRootDFileSystem
except ImportError:
    XRootDFileSystem = None


def _normalize_root(value: str) -> str:
    root = value.strip()
    if not root or not root.startswith("/"):
        raise ValueError("XRootD root must be an absolute directory path.")
    return "/" + posixpath.normpath(root).lstrip("/")


def _normalize_relative_path(path: str) -> str:
    # Normalize a relative path: an absolute normpath would hide leading '..'.
    relative = posixpath.normpath(path.lstrip("/"))
    if relative == ".." or relative.startswith("../"):
        raise MessageException("Invalid path: outside configured XRootD root.")
    return "" if relative == "." else relative


class XRootDFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    root: str | TemplateExpansion
    hostid: str | TemplateExpansion
    timeout: int | TemplateExpansion = 30
    writable: Literal[False] = False

    @field_validator("root")
    @classmethod
    def validate_root(cls, value: str) -> str:
        # Cheetah expressions must be validated after expansion, at runtime.
        return value if "$" in value else _normalize_root(value)


class XRootDFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    root: str
    hostid: str
    timeout: int = 30
    writable: Literal[False] = False

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
            skip_instance_cache=True,
            asynchronous=False,
            **cache_options,
        )

    def _to_filesystem_path(self, path: str, config: XRootDFileSourceConfiguration) -> str:
        relative_path = _normalize_relative_path(path)
        return f"{config.root.rstrip('/')}/{relative_path}" if relative_path else config.root

    def _adapt_entry_path(self, filesystem_path: str, config: XRootDFileSourceConfiguration) -> str:
        normalized_path = "/" + filesystem_path.lstrip("/")
        if normalized_path == config.root:
            return "/"
        root_prefix = config.root.rstrip("/") + "/"
        if not normalized_path.startswith(root_prefix):
            raise MessageException(f"Unexpected XRootD listing entry outside configured root: {filesystem_path!r}")
        relative_path = _normalize_relative_path(normalized_path[len(root_prefix) :])
        return f"/{relative_path}"

    def _write_from(
        self,
        _target_path: str,
        _native_path: str,
        _context: FilesSourceRuntimeContext[XRootDFileSourceConfiguration],
    ) -> None:
        raise MessageException("XRootD file sources are read-only and do not support exporting files.")

    def get_scheme(self) -> str:
        return self.scheme if self.scheme and self.scheme != DEFAULT_SCHEME else "xrootd"


__all__ = ("XRootDFilesSource",)
