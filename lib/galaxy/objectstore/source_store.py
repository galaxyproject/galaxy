"""An object store that owns a FilesSource and delegates all I/O to it.

Stage 2 of the ObjectStore/FilesSource unification (see
``doc/source/dev/objectstore_filesource_unification.md``). Unlike the Stage 1
``DelegatingObjectStore`` (which keeps the cache in the object store), this store has no
cache of its own: ``get_filename`` resolves through the source's ``get_local_path``. So a
``PosixFilesSource`` yields a zero-copy real path (the ``DiskObjectStore`` role) and a
``CachingFilesSource`` yields a cache path (the ``S3ObjectStore`` role) -- one object store
class for both, and the disk special-case disappears.

Addressing (the ``directory_hash_id`` key), quota, ``store_by`` and the other
object-store-only concerns stay here; the transport and any cache live in the source.

``base_dir`` operations (``job_work`` / ``temp``) are always-local scratch directories,
independent of the dataset backend -- every object store handles them on the local
filesystem -- so they bypass the source and use ``self.extra_dirs[base_dir]`` directly.
"""

import logging
import os
import shutil
import tempfile
from typing import (
    Protocol,
    runtime_checkable,
)

from galaxy.exceptions import (
    ObjectInvalid,
    ObjectNotFound,
)
from galaxy.objectstore import ConcreteObjectStore
from galaxy.util import (
    directory_hash_id,
    unlink,
)
from galaxy.util.path import safe_relpath

log = logging.getLogger(__name__)


@runtime_checkable
class ObjectStoreFilesSource(Protocol):
    """The FilesSource surface an object store needs: whole-file I/O plus local-path resolve.

    Both a raw ``BaseFilesSource`` (e.g. ``PosixFilesSource``) and a ``CachingFilesSource``
    satisfy this structurally.
    """

    def exists(self, path: str, user_context=None) -> bool: ...

    def size(self, path: str, user_context=None) -> int: ...

    def write_from(self, target_path: str, native_path: str, user_context=None, opts=None) -> str: ...

    def remove(self, path: str, recursive: bool = False, user_context=None) -> bool: ...

    def get_local_path(self, path: str, user_context=None) -> str: ...

    def usage_percent(self, user_context=None) -> float | None: ...


class SourceObjectStore(ConcreteObjectStore):
    store_type = "source"

    def __init__(self, config, config_dict, source: ObjectStoreFilesSource | None = None):
        super().__init__(config, config_dict)
        extra_dirs = {e["type"]: e["path"] for e in config_dict.get("extra_dirs", [])}
        self.extra_dirs.update(extra_dirs)
        # Retained for to_dict round-tripping when the source is built from config.
        self._files_source_config = config_dict.get("files_source")
        self._cache_config = config_dict.get("cache")
        self._source = source if source is not None else self._build_source(config, config_dict)

    @classmethod
    def parse_xml(cls, config_xml):
        raise NotImplementedError("The 'source' object store type must be configured via YAML, not XML.")

    @staticmethod
    def _build_source(config, config_dict) -> ObjectStoreFilesSource:
        """Construct the backing FilesSource from a ``files_source`` plugin config.

        A ``cache`` section wraps the (remote) source in a ``CachingFilesSource`` so its
        objects resolve to a local path; a bare local source (posix) needs no cache.
        """
        from galaxy.files.plugins import (
            FileSourcePluginLoader,
            FileSourcePluginsConfig,
        )
        from galaxy.util.plugin_config import plugin_source_from_dict

        files_source_config = config_dict.get("files_source")
        if not files_source_config:
            raise Exception("A 'source' object store requires a 'files_source' configuration.")
        if hasattr(config, "user_library_import_symlink_allowlist"):
            fs_config = FileSourcePluginsConfig.from_app_config(config)
        else:
            fs_config = FileSourcePluginsConfig()
        source_dict = dict(files_source_config)
        source_dict.setdefault("id", "objectstore_source")
        loader = FileSourcePluginLoader()
        inner = loader.load_plugins(plugin_source_from_dict([source_dict]), fs_config)[0]

        cache_dict = config_dict.get("cache")
        if cache_dict is not None:
            from ._caching_source import CachingFilesSource

            staging_path = cache_dict.get("path") or config.object_store_cache_path
            cache_size = cache_dict.get("size") or config.object_store_cache_size
            return CachingFilesSource(inner, staging_path=staging_path, cache_size=cache_size)
        return inner

    def to_dict(self):
        rval = super().to_dict()
        if self._files_source_config is not None:
            rval["files_source"] = self._files_source_config
        if self._cache_config is not None:
            rval["cache"] = self._cache_config
        return rval

    def _rel_path(
        self, obj, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False, **kwargs
    ) -> str:
        if alt_name and not safe_relpath(alt_name):
            log.warning("alt_name would locate path outside dir: %s", alt_name)
            raise ObjectInvalid("The requested object is invalid")
        object_id = self._get_object_id(obj)
        rel_path = os.path.join(*directory_hash_id(object_id))
        if obj_dir:
            rel_path = os.path.join(rel_path, str(object_id))
        if extra_dir is not None:
            rel_path = os.path.join(extra_dir, rel_path) if extra_dir_at_root else os.path.join(rel_path, extra_dir)
        # Directories are represented with a trailing slash, matching the remote stores.
        rel_path = f"{rel_path}/"
        if not dir_only:
            rel_path = os.path.join(rel_path, alt_name if alt_name else f"dataset_{object_id}.dat")
        return rel_path

    # --- always-local scratch dirs (job_work / temp) ----------------------------------------

    def _local_path(
        self,
        obj,
        base_dir=None,
        dir_only=False,
        extra_dir=None,
        extra_dir_at_root=False,
        alt_name=None,
        obj_dir=False,
        **kwargs,
    ) -> str:
        if alt_name and not safe_relpath(alt_name):
            raise ObjectInvalid("The requested object is invalid")
        base = os.path.abspath(self.extra_dirs[base_dir])
        object_id = self._get_object_id(obj)
        rel_path = os.path.join(*directory_hash_id(object_id))
        if obj_dir:
            rel_path = os.path.join(rel_path, str(object_id))
        if extra_dir is not None:
            rel_path = os.path.join(extra_dir, rel_path) if extra_dir_at_root else os.path.join(rel_path, extra_dir)
        path = os.path.join(base, rel_path)
        if not dir_only:
            path = os.path.join(path, alt_name if alt_name else f"dataset_{object_id}.dat")
        return os.path.abspath(path)

    # --- ObjectStore contract ---------------------------------------------------------------

    def _exists(self, obj, **kwargs) -> bool:
        if kwargs.get("base_dir"):
            return os.path.exists(self._local_path(obj, **kwargs))
        return self._source.exists(self._rel_path(obj, **kwargs))

    def _create(self, obj, **kwargs):
        if kwargs.get("base_dir"):
            path = self._local_path(obj, **kwargs)
            directory = path if kwargs.get("dir_only") else os.path.dirname(path)
            os.makedirs(directory, exist_ok=True)
            if not kwargs.get("dir_only") and not os.path.exists(path):
                open(path, "w").close()
            return self
        if not self._exists(obj, **kwargs):
            if kwargs.get("dir_only"):
                # dir_only creation for the dataset source (composite / extra-files dirs) is
                # deferred in this prototype.
                return self
            rel_path = self._rel_path(obj, **kwargs)
            fd, tmp = tempfile.mkstemp()
            try:
                os.close(fd)
                self._source.write_from(rel_path, tmp)
            finally:
                unlink(tmp, ignore_errors=True)
        return self

    def _empty(self, obj, **kwargs) -> bool:
        if self._exists(obj, **kwargs):
            return self._size(obj, **kwargs) == 0
        raise ObjectNotFound(f"objectstore.empty, object does not exist: {obj}, kwargs: {kwargs}")

    def _size(self, obj, **kwargs) -> int:
        if not self._exists(obj, **kwargs):
            return 0
        path_fn = self._local_path if kwargs.get("base_dir") else None
        try:
            if path_fn is not None:
                return os.path.getsize(path_fn(obj, **kwargs))
            return self._source.size(self._rel_path(obj, **kwargs))
        except OSError:
            return 0

    def _get_filename(self, obj, **kwargs) -> str:
        if kwargs.get("base_dir"):
            path = self._local_path(obj, **kwargs)
            if not os.path.exists(path):
                raise ObjectNotFound(f"objectstore.get_filename, object does not exist: {obj}, kwargs: {kwargs}")
            return path
        try:
            return self._source.get_local_path(self._rel_path(obj, **kwargs))
        except FileNotFoundError:
            raise ObjectNotFound(f"objectstore.get_filename, object does not exist: {obj}, kwargs: {kwargs}")

    def _get_data(self, obj, start=0, count=-1, **kwargs):
        with open(self._get_filename(obj, **kwargs)) as data_file:
            data_file.seek(start)
            return data_file.read(count)

    def _update_from_file(self, obj, file_name=None, create: bool = False, preserve_symlinks: bool = False, **kwargs):
        if kwargs.get("base_dir"):
            if create:
                self._create(obj, **kwargs)
            if file_name:
                path = self._local_path(obj, **kwargs)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                shutil.copy(os.path.abspath(file_name), path)
            return
        if file_name:
            if create or self._exists(obj, **kwargs):
                self._source.write_from(self._rel_path(obj, **kwargs), os.path.abspath(file_name))
        elif create:
            self._create(obj, **kwargs)

    def _delete(self, obj, entire_dir: bool = False, **kwargs) -> bool:
        if kwargs.get("base_dir"):
            path = self._local_path(obj, **kwargs)
            try:
                if entire_dir and (kwargs.get("extra_dir") or kwargs.get("obj_dir")):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                return True
            except FileNotFoundError:
                return True
            except OSError:
                log.exception("%s delete error", path)
                return False
        rel_path = self._rel_path(obj, **kwargs)
        recursive = bool(entire_dir and (kwargs.get("extra_dir") or kwargs.get("obj_dir")))
        try:
            return self._source.remove(rel_path, recursive=recursive)
        except FileNotFoundError:
            return True

    def _get_object_url(self, obj, **kwargs):
        return None

    def _get_store_usage_percent(self, **kwargs):
        usage = self._source.usage_percent()
        return usage if usage is not None else 0.0
