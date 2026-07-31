"""An object store whose remote transport is pluggable.

Stage 1 of the ObjectStore/FilesSource unification (see
``doc/source/dev/objectstore_filesource_unification.md``). The entire caching layer of
:class:`~galaxy.objectstore._caching_base.CachingConcreteObjectStore` is left unchanged;
only the backend I/O hooks are routed to an injected
:class:`~galaxy.objectstore._transport.ObjectStoreTransport`. Pointing that transport at
a local directory (or, later, at a ``FilesSource`` adapter) exercises the exact seam a
cloud backend uses, with no credentials required.
"""

import logging
import os

from ._caching_base import CachingConcreteObjectStore
from ._transport import ObjectStoreTransport
from .caching import enable_cache_monitor

log = logging.getLogger(__name__)


class DelegatingObjectStore(CachingConcreteObjectStore):
    store_type = "delegating"

    def __init__(self, config, config_dict, transport: ObjectStoreTransport):
        super().__init__(config, config_dict)
        self.cache_monitor = None
        cache_dict = config_dict.get("cache") or {}
        self.enable_cache_monitor, self.cache_monitor_interval = enable_cache_monitor(config, config_dict)
        self.cache_size = cache_dict.get("size") or self.config.object_store_cache_size
        self.staging_path = cache_dict.get("path") or self.config.object_store_cache_path
        self.cache_updated_data = cache_dict.get("cache_updated_data", True)
        extra_dirs = {e["type"]: e["path"] for e in config_dict.get("extra_dirs", [])}
        self.extra_dirs.update(extra_dirs)
        self._transport = transport
        self._ensure_staging_path_writable()
        self._start_cache_monitor_if_needed()

    def _download(self, rel_path: str) -> bool:
        if not self._caching_allowed(rel_path):
            return False
        cache_path = self._get_cache_path(rel_path)
        try:
            with self._atomic_download(cache_path) as tmp:
                self._transport.download(rel_path, tmp)
            return True
        except Exception:
            log.exception("Failed to download '%s' through transport", rel_path)
            return False

    def _push_file_to_path(self, rel_path: str, source_file: str) -> bool:
        return self._transport.upload_file(rel_path, source_file)

    def _push_string_to_path(self, rel_path: str, from_string: str) -> bool:
        return self._transport.upload_string(rel_path, from_string)

    def _exists_remotely(self, rel_path: str) -> bool:
        return self._transport.exists(rel_path)

    def _get_remote_size(self, rel_path: str) -> int:
        return self._transport.size(rel_path)

    def _delete_existing_remote(self, rel_path: str) -> bool:
        return self._transport.delete(rel_path)

    def _delete_remote_all(self, rel_path: str) -> bool:
        return self._transport.delete_prefix(rel_path)

    def _download_directory_into_cache(self, rel_path: str, cache_path: str) -> None:
        for key in self._transport.list_prefix(rel_path):
            local_file_path = os.path.join(cache_path, os.path.relpath(key, rel_path))
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            with self._atomic_download(local_file_path) as tmp:
                self._transport.download(key, tmp)

    def shutdown(self):
        self._shutdown_cache_monitor()
