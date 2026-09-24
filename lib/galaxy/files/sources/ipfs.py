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
    from ipfsspec import AsyncIPFSFileSystem
except ImportError:
    AsyncIPFSFileSystem = None


def _normalize_root(value: str) -> str:
    root = value.strip().strip("/")
    if not root:
        raise ValueError("IPFS root CID is required.")
    if root in (".", "..") or any(c.isspace() or c in "/\\%?#" for c in root):
        raise ValueError("IPFS root must be a single CID, without a URL or subpath.")
    return root


def _normalize_relative_path(path: str) -> str:
    # Normalize a relative path: an absolute normpath would hide leading '..'.
    relative = posixpath.normpath(path.lstrip("/"))
    if relative == ".." or relative.startswith("../"):
        raise MessageException("Invalid path: outside configured IPFS root.")
    return "" if relative == "." else relative


class IPFSFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    root: str | TemplateExpansion
    gateway_url: str | TemplateExpansion
    writable: Literal[False] = False

    @field_validator("root")
    @classmethod
    def validate_root(cls, value: str) -> str:
        # Cheetah expressions must be validated after expansion, at runtime.
        return value if "$" in value else _normalize_root(value)


class IPFSFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    root: str
    gateway_url: str
    writable: Literal[False] = False

    @field_validator("root")
    @classmethod
    def validate_root(cls, value: str) -> str:
        return _normalize_root(value)


class IPFSFilesSource(FsspecFilesSource[IPFSFileSourceTemplateConfiguration, IPFSFileSourceConfiguration]):
    plugin_type = "ipfs"
    required_module = AsyncIPFSFileSystem
    required_package = "ipfsspec"

    template_config_class = IPFSFileSourceTemplateConfiguration
    resolved_config_class = IPFSFileSourceConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[IPFSFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ) -> AbstractFileSystem:
        if AsyncIPFSFileSystem is None:
            raise self.required_package_exception

        return AsyncIPFSFileSystem(
            gateway_addr=context.config.gateway_url.rstrip("/"),
            asynchronous=False,
            **cache_options,
        )

    def _to_filesystem_path(self, path: str, config: IPFSFileSourceConfiguration) -> str:
        relative_path = _normalize_relative_path(path)
        return f"{config.root}/{relative_path}" if relative_path else config.root

    def _adapt_entry_path(self, filesystem_path: str, config: IPFSFileSourceConfiguration) -> str:
        normalized_path = filesystem_path.lstrip("/")
        if normalized_path == config.root:
            return "/"
        root_prefix = f"{config.root}/"
        if not normalized_path.startswith(root_prefix):
            raise MessageException(f"Unexpected IPFS listing entry outside configured root: {filesystem_path!r}")
        relative_path = _normalize_relative_path(normalized_path[len(root_prefix) :])
        return f"/{relative_path}"

    def _write_from(
        self,
        _target_path: str,
        _native_path: str,
        _context: FilesSourceRuntimeContext[IPFSFileSourceConfiguration],
    ):
        raise MessageException("IPFS file sources are read-only and do not support exporting files.")

    def get_scheme(self) -> str:
        return self.scheme if self.scheme and self.scheme != DEFAULT_SCHEME else "ipfs"


__all__ = ("IPFSFilesSource",)
