"""In-memory filesystem implementation for Galaxy files sources."""

import logging
from typing import Optional

from fsspec import AbstractFileSystem
from fsspec.implementations.memory import MemoryFileSystem

from galaxy.files import OptionalUserContext
from galaxy.files.sources._fsspec import FsspecFilesSource
from . import FilesSourceOptions

log = logging.getLogger(__name__)


class MemoryFilesSource(FsspecFilesSource):
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

    def _open_fs(
        self, user_context: OptionalUserContext = None, opts: Optional[FilesSourceOptions] = None
    ) -> AbstractFileSystem:
        props = self._serialization_props(user_context)
        extra_props = opts.extra_props or {} if opts else {}
        fs = MemoryFileSystem(**{**props, **extra_props})
        return fs

    def get_scheme(self) -> str:
        return "memory"


__all__ = ("MemoryFilesSource",)
