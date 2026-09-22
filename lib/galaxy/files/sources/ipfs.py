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
        root = config.root.strip("/")
        relative_path = path.lstrip("/")
        return f"{root}/{relative_path}" if relative_path else root

    def _adapt_entry_path(self, filesystem_path: str, config: IPFSFileSourceConfiguration) -> str:
        root = config.root.strip("/")
        normalized_path = filesystem_path.lstrip("/")
        if normalized_path == root:
            return "/"
        root_prefix = f"{root}/"
        return f"/{normalized_path.removeprefix(root_prefix)}"

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
