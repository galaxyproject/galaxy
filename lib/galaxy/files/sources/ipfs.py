from typing import Literal

from fsspec import AbstractFileSystem

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


class IPFSFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    root: str | TemplateExpansion
    gateway_url: str | TemplateExpansion
    writable: Literal[False] = False


class IPFSFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    root: str
    gateway_url: str
    writable: Literal[False] = False


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
        if path in ("", "/"):
            return config.root.strip("/")
        return path.lstrip("/")

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
