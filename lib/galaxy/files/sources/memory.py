"""In-memory filesystem implementation for Galaxy files sources."""

import logging

from fsspec import AbstractFileSystem
from fsspec.implementations.memory import MemoryFileSystem

from galaxy.files.models import FilesSourceRuntimeContext
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)

log = logging.getLogger(__name__)


class MemoryFilesSource(
    FsspecFilesSource[FsspecBaseFileSourceTemplateConfiguration, FsspecBaseFileSourceConfiguration]
):
    """A FilesSource plugin for in-memory filesystem operations.

    This implementation uses fsspec's MemoryFileSystem to provide
    a transient, in-memory file storage backend. This is primarily
    useful for testing, do not use in production environments.

    Note: All data stored in this filesystem is volatile and will
    be lost when the instance is destroyed. Due to MemoryFileSystem's
    implementation, all instances share the same memory store,
    so operations on one instance will affect all others.
    """

    plugin_type = "memory"
    required_module = MemoryFileSystem
    required_package = "fsspec"

    template_config_class = FsspecBaseFileSourceTemplateConfiguration
    resolved_config_class = FsspecBaseFileSourceConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[FsspecBaseFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ) -> AbstractFileSystem:
        fs = MemoryFileSystem(**cache_options)
        return fs

    def get_scheme(self) -> str:
        return "memory"


__all__ = ("MemoryFilesSource",)
