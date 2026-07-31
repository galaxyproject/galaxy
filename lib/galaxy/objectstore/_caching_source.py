"""A cache wrapper that gives any whole-file FilesSource a stable local path.

Stage 2 of the ObjectStore/FilesSource unification (see
``doc/source/dev/objectstore_filesource_unification.md``). This wraps a raw FilesSource with
a :class:`~galaxy.objectstore.caching.CacheArea` -- the *same* cache implementation the
caching object stores use -- and adds the one primitive a raw remote source lacks:
``get_local_path``, which resolves a key to a real, seekable local path by pulling it into
the cache on demand. A local source (posix) needs no wrapper; a remote source (s3, ...) is
wrapped so an object store built on it can honor ``get_filename``.

Placed in the object store package for now because it reuses ``galaxy.objectstore.caching``;
a full Stage 2 would relocate the cache primitives to a neutral module so this can live in
``galaxy.files``. It keeps no runtime dependency on ``galaxy.files`` (the wrapped source is
imported only under ``TYPE_CHECKING``).
"""

import logging
import os
import shutil
from typing import TYPE_CHECKING

from .caching import CacheArea

if TYPE_CHECKING:
    from galaxy.files import OptionalUserContext
    from galaxy.files.sources import BaseFilesSource

log = logging.getLogger(__name__)


class CachingFilesSource:
    """Wraps a raw FilesSource with a local cache so it can resolve stable local paths."""

    def __init__(
        self,
        inner: "BaseFilesSource",
        staging_path: str,
        cache_size: int = -1,
        user_context: "OptionalUserContext" = None,
    ):
        self._inner = inner
        self._cache = CacheArea(staging_path, cache_size)
        self._cache.ensure_writable()
        self._user_context = user_context

    def _caching_allowed(self, path: str) -> bool:
        remote_size = self._inner.size(path, user_context=self._user_context)
        return self._cache.fits(remote_size or 0)

    # --- FilesSource-shaped interface consumed by the object store ---

    def exists(self, path: str, user_context: "OptionalUserContext" = None) -> bool:
        return self._cache.contains_nonempty(path) or self._inner.exists(
            path, user_context=user_context or self._user_context
        )

    def size(self, path: str, user_context: "OptionalUserContext" = None) -> int:
        if self._cache.contains_nonempty(path):
            return self._cache.size(path)
        return self._inner.size(path, user_context=user_context or self._user_context)

    def get_local_path(self, path: str, user_context: "OptionalUserContext" = None) -> str:
        cache_path = self._cache.path(path)
        if self._cache.contains_nonempty(path):
            return cache_path
        if not self._caching_allowed(path):
            raise Exception(f"File {path} is larger than the configured cache allows.")
        self._cache.makedirs_for(path)
        with self._cache.atomic_write(cache_path) as tmp:
            self._inner.realize_to(path, tmp, user_context=user_context or self._user_context)
        return cache_path

    def realize_to(self, source_path: str, native_path: str, user_context: "OptionalUserContext" = None, opts=None):
        self._inner.realize_to(source_path, native_path, user_context=user_context or self._user_context, opts=opts)

    def write_from(
        self, target_path: str, native_path: str, user_context: "OptionalUserContext" = None, opts=None
    ) -> str:
        # Push to the backing store (the source of truth), then warm the cache.
        result = self._inner.write_from(
            target_path, native_path, user_context=user_context or self._user_context, opts=opts
        )
        cache_path = self._cache.path(target_path)
        self._cache.makedirs_for(target_path)
        if os.path.abspath(native_path) != cache_path:
            shutil.copyfile(native_path, cache_path)
        return result or target_path

    def remove(self, path: str, recursive: bool = False, user_context: "OptionalUserContext" = None) -> bool:
        if recursive:
            self._cache.evict_dir(path)
        else:
            self._cache.evict(path)
        return self._inner.remove(path, recursive=recursive, user_context=user_context or self._user_context)

    def usage_percent(self, user_context: "OptionalUserContext" = None) -> float | None:
        return self._inner.usage_percent(user_context=user_context or self._user_context)
