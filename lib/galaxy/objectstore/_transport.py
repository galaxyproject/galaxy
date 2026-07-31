"""Whole-file, key-addressed transport for caching object stores.

Stage 1 of the ObjectStore/FilesSource unification (see
``doc/source/dev/objectstore_filesource_unification.md``). Below its cache, a
:class:`~galaxy.objectstore._caching_base.CachingConcreteObjectStore` needs only a
whole-file get/put/exists/size/delete interface keyed on a relative path -- which is
essentially the ``FilesSource`` contract with the method names filed off. This module
names that seam as :class:`ObjectStoreTransport` and provides a local-filesystem
implementation used both as a test stand-in for remote stores and, eventually, as the
``DiskObjectStore`` backend.
"""

import os
import shutil
import tempfile
from collections.abc import Iterable
from typing import (
    Protocol,
    runtime_checkable,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from galaxy.files import OptionalUserContext
    from galaxy.files.sources import BaseFilesSource


@runtime_checkable
class ObjectStoreTransport(Protocol):
    """The whole-file transport a caching object store delegates its backend I/O to.

    Every method is keyed on ``rel_path`` -- a path relative to the transport root such
    as ``000/001/dataset_1.dat``. Directory keys carry a trailing ``/`` (matching how
    ``CachingConcreteObjectStore._construct_path`` builds them).
    """

    def download(self, rel_path: str, dest_path: str) -> None:
        """Copy the object at ``rel_path`` to the local ``dest_path``; raise if absent."""

    def upload_file(self, rel_path: str, source_path: str) -> bool:
        """Store the local file ``source_path`` as the object at ``rel_path``."""

    def upload_string(self, rel_path: str, data: str) -> bool:
        """Store ``data`` as the object at ``rel_path``."""

    def exists(self, rel_path: str) -> bool:
        """Return whether ``rel_path`` (or, for a trailing-slash key, any object under it) exists."""

    def size(self, rel_path: str) -> int:
        """Return the size of the object at ``rel_path`` in bytes."""

    def delete(self, rel_path: str) -> bool:
        """Delete the single object at ``rel_path``."""

    def delete_prefix(self, rel_path: str) -> bool:
        """Delete every object under the ``rel_path`` prefix."""

    def list_prefix(self, rel_path: str) -> Iterable[str]:
        """Yield the key of every object under the ``rel_path`` prefix."""


class LocalTransport:
    """A local-filesystem :class:`ObjectStoreTransport` rooted at a directory.

    Keys are paths relative to ``root``. This doubles as the future
    ``DiskObjectStore`` backend and as a credential-free stand-in for remote stores
    in tests.
    """

    def __init__(self, root: str):
        self.root = os.path.abspath(root)

    def _full(self, rel_path: str) -> str:
        return os.path.join(self.root, rel_path)

    def download(self, rel_path: str, dest_path: str) -> None:
        shutil.copyfile(self._full(rel_path), dest_path)

    def upload_file(self, rel_path: str, source_path: str) -> bool:
        full = self._full(rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        shutil.copyfile(source_path, full)
        return True

    def upload_string(self, rel_path: str, data: str) -> bool:
        full = self._full(rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as fh:
            fh.write(data)
        return True

    def exists(self, rel_path: str) -> bool:
        if rel_path.endswith("/"):
            return any(True for _ in self.list_prefix(rel_path))
        return os.path.isfile(self._full(rel_path))

    def size(self, rel_path: str) -> int:
        return os.path.getsize(self._full(rel_path))

    def delete(self, rel_path: str) -> bool:
        os.remove(self._full(rel_path))
        return True

    def delete_prefix(self, rel_path: str) -> bool:
        shutil.rmtree(self._full(rel_path), ignore_errors=True)
        return True

    def list_prefix(self, rel_path: str) -> Iterable[str]:
        base = self._full(rel_path)
        if not os.path.isdir(base):
            return
        for dirpath, _, filenames in os.walk(base):
            for filename in filenames:
                yield os.path.relpath(os.path.join(dirpath, filename), self.root)


class FilesSourceTransport:
    """An :class:`ObjectStoreTransport` backed by a ``galaxy.files`` FilesSource.

    This is the crux of the unification: the object store's whole-file transport seam is
    satisfied directly by a FilesSource's ``realize_to`` / ``write_from`` / ``exists`` /
    ``size`` / ``remove`` / ``list``. The ``BaseFilesSource`` type is imported only under
    ``TYPE_CHECKING`` so the object store keeps no runtime dependency on ``galaxy.files``.

    Object stores are admin-configured and not user-scoped, so ``user_context`` defaults to
    ``None`` (the FilesSource then skips per-user access checks). See
    ``doc/source/dev/objectstore_filesource_unification.md``.
    """

    def __init__(self, files_source: "BaseFilesSource", user_context: "OptionalUserContext" = None):
        self._source = files_source
        self._user_context = user_context

    def download(self, rel_path: str, dest_path: str) -> None:
        self._source.realize_to(rel_path, dest_path, user_context=self._user_context)

    def upload_file(self, rel_path: str, source_path: str) -> bool:
        self._source.write_from(rel_path, source_path, user_context=self._user_context)
        return True

    def upload_string(self, rel_path: str, data: str) -> bool:
        fd, tmp = tempfile.mkstemp()
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(data)
            self._source.write_from(rel_path, tmp, user_context=self._user_context)
        finally:
            os.remove(tmp)
        return True

    def exists(self, rel_path: str) -> bool:
        return self._source.exists(rel_path, user_context=self._user_context)

    def size(self, rel_path: str) -> int:
        return self._source.size(rel_path, user_context=self._user_context)

    def delete(self, rel_path: str) -> bool:
        return self._source.remove(rel_path, user_context=self._user_context)

    def delete_prefix(self, rel_path: str) -> bool:
        return self._source.remove(rel_path, recursive=True, user_context=self._user_context)

    def list_prefix(self, rel_path: str) -> Iterable[str]:
        entries, _ = self._source.list(rel_path, recursive=True, user_context=self._user_context)
        for entry in entries:
            if getattr(entry, "class_", None) == "File":
                yield entry.path
