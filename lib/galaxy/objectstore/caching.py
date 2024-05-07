"""
"""

import logging
import os
import threading
import time
from math import inf
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from typing_extensions import NamedTuple

from galaxy.exceptions import (
    ObjectInvalid,
    ObjectNotFound,
)
from galaxy.util import (
    directory_hash_id,
    ExecutionTimer,
    nice_size,
    string_as_bool,
)
from galaxy.util.path import safe_relpath
from galaxy.util.sleeper import Sleeper
from ._util import fix_permissions

log = logging.getLogger(__name__)


ONE_GIGA_BYTE = 1024 * 1024 * 1024


FileListT = List[Tuple[time.struct_time, str, int]]


class CacheTarget(NamedTuple):
    path: str
    size: int  # cache size in gigabytes
    limit: float  # cache limit as a percent

    def fits_in_cache(self, bytes: int) -> bool:
        # if we don't have a positive cache size - interpret it as an unbounded
        # object store
        if not (self.size > 0):
            return True

        if bytes > (self.size * ONE_GIGA_BYTE * self.limit):
            return False
        return True

    @property
    def log_description(self) -> str:
        return f"{self.limit} percent of {self.size} gigabytes"


def check_caches(targets: List[CacheTarget]):
    for target in targets:
        check_cache(target)


def check_cache(cache_target: CacheTarget):
    """Run a step of the cache monitor."""
    total_size, file_list = _get_cache_size_files(cache_target.path)
    # Sort the file list (based on access time)
    file_list.sort()
    # Initiate cleaning once we reach cache_monitor_cache_limit percentage of the defined cache size?
    # Convert GBs to bytes for comparison
    cache_size_in_gb = cache_target.size * ONE_GIGA_BYTE
    cache_limit = cache_size_in_gb * cache_target.limit
    if total_size > cache_limit:
        log.debug(
            "Initiating cache cleaning: current cache size: %s; clean until smaller than: %s",
            nice_size(total_size),
            nice_size(cache_limit),
        )
        # How much to delete? If simply deleting up to the cache-10% limit,
        # is likely to be deleting frequently and may run the risk of hitting
        # the limit - maybe delete additional #%?
        # For now, delete enough to leave at least 10% of the total cache free
        delete_this_much = total_size - cache_limit
        _clean_cache(file_list, delete_this_much)


def reset_cache(cache_target: CacheTarget):
    _, file_list = _get_cache_size_files(cache_target.path)
    _clean_cache(file_list, inf)


def _clean_cache(file_list: FileListT, delete_this_much: float) -> None:
    """Keep deleting files from the file_list until the size of the deleted
    files is greater than the value in delete_this_much parameter.
    :param file_list: List of candidate files that can be deleted. This method
        will start deleting files from the beginning of the list so the list
        should be sorted accordingly. The list must contains 3-element tuples,
        positioned as follows: position 0 holds file last accessed timestamp
        (as time.struct_time), position 1 holds file path, and position 2 has
        file size (e.g., (<access time>, /mnt/data/dataset_1.dat), 472394)
    :param delete_this_much: Total size of files, in bytes, that should be deleted.
    """
    # Keep deleting datasets from file_list until deleted_amount does not
    # exceed delete_this_much; start deleting from the front of the file list,
    # which assumes the oldest files come first on the list.
    deleted_amount = 0
    for entry in file_list:
        if deleted_amount < delete_this_much:
            deleted_amount += entry[2]
            os.remove(entry[1])
        else:
            log.debug("Cache cleaning done. Total space freed: %s", nice_size(deleted_amount))
            return


def _get_cache_size_files(cache_path) -> Tuple[int, FileListT]:
    """Returns cache size and cache files.

    For each file, we get last access time, file path, and file size.
    """
    cache_size = 0
    file_list = []

    for dirpath, _, filenames in os.walk(cache_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            file_size = os.path.getsize(file_path)
            cache_size += file_size
            # Get the time given file was last accessed
            last_access_time = time.localtime(os.stat(file_path)[7])
            # Compose a tuple of the access time and the file path
            file_tuple = last_access_time, file_path, file_size
            file_list.append(file_tuple)
    return cache_size, file_list


def parse_caching_config_dict_from_xml(config_xml):
    cache_els = config_xml.findall("cache")
    if len(cache_els) > 0:
        c_xml = config_xml.findall("cache")[0]
        cache_size = float(c_xml.get("size", -1))
        staging_path = c_xml.get("path", None)
        monitor = c_xml.get("monitor", "auto")
        cache_updated_data = string_as_bool(c_xml.get("cache_updated_data", "True"))

        cache_dict = {
            "size": cache_size,
            "path": staging_path,
            "monitor": monitor,
            "cache_updated_data": cache_updated_data,
        }
    else:
        cache_dict = {}
    return cache_dict


def configured_cache_size(config, config_dict) -> int:
    cache_config_dict = config_dict.get("cache") or {}
    cache_size = cache_config_dict.get("size") or config.object_store_cache_size
    if cache_size != -1:
        # Convert admin-set GBs to bytes internally for quick comparison
        cache_size = cache_size * ONE_GIGA_BYTE
    return cache_size


def enable_cache_monitor(config, config_dict) -> Tuple[bool, int]:
    cache_config_dict = config_dict.get("cache") or {}
    default_interval = getattr(config, "object_store_cache_monitor_interval", 600)
    interval = cache_config_dict.get("monitor_interval") or default_interval

    disable_process_management = getattr(config, "disable_process_management", None)
    if disable_process_management is True:
        return False, interval

    if config_dict.get("enable_cache_monitor", False) is False:
        return False, interval

    default_cache_driver = getattr(config, "object_store_cache_monitor_driver", "auto")
    monitor = cache_config_dict.get("monitor", default_cache_driver)
    if monitor == "auto":
        monitor = "celery" if getattr(config, "enable_celery_tasks", False) else "inprocess"

    return monitor == "inprocess", interval


class InProcessCacheMonitor:
    def __init__(self, cache_target: CacheTarget, interval: int = 30, initial_sleep: Optional[int] = 2):
        # This Event object is initialized to False
        # It is set to True in shutdown(), causing
        # the cache monitor thread to return/terminate
        self.stop_cache_monitor_event = threading.Event()
        # Helper for interruptable sleep
        self.sleeper = Sleeper()

        self.cache_target = cache_target
        self.interval = interval
        self.initial_sleep = initial_sleep

        self.cache_monitor_thread = threading.Thread(
            target=self._cache_monitor,
            name="CacheMonitorThread",
        )
        self.cache_monitor_thread.start()

    def _cache_monitor(self):
        if self.initial_sleep is not None:
            time.sleep(
                self.initial_sleep
            )  # startup sleep hack - probably originally implemented to prevent contention at app startup
        while not self.stop_cache_monitor_event.is_set():
            check_cache(self.cache_target)
            self.sleeper.sleep(self.interval)

    def shutdown(self):
        # Set the event object so the cache monitor thread terminates
        self.stop_cache_monitor_event.set()

        # wake up from sleeping
        self.sleeper.wake()

        # Wait for the cache monitor thread to join before ending
        self.cache_monitor_thread.join(5)


# mixin for object stores using a cache directory
class UsesCache:
    staging_path: str
    extra_dirs: Dict[str, str]
    config: Any

    def _construct_path(
        self,
        obj,
        base_dir=None,
        dir_only=None,
        extra_dir=None,
        extra_dir_at_root=False,
        alt_name=None,
        obj_dir=False,
        in_cache=False,
        **kwargs,
    ):
        # extra_dir should never be constructed from provided data but just
        # make sure there are no shenannigans afoot
        if extra_dir and extra_dir != os.path.normpath(extra_dir):
            log.warning("extra_dir is not normalized: %s", extra_dir)
            raise ObjectInvalid("The requested object is invalid")
        # ensure that any parent directory references in alt_name would not
        # result in a path not contained in the directory path constructed here
        if alt_name:
            if not safe_relpath(alt_name):
                log.warning("alt_name would locate path outside dir: %s", alt_name)
                raise ObjectInvalid("The requested object is invalid")
            # alt_name can contain parent directory references, but S3 will not
            # follow them, so if they are valid we normalize them out
            alt_name = os.path.normpath(alt_name)

        object_id = self._get_object_id(obj)
        rel_path = os.path.join(*directory_hash_id(object_id))

        if extra_dir is not None:
            if extra_dir_at_root:
                rel_path = os.path.join(extra_dir, rel_path)
            else:
                rel_path = os.path.join(rel_path, extra_dir)

        # for JOB_WORK directory
        if obj_dir:
            rel_path = os.path.join(rel_path, str(object_id))
        if base_dir:
            base = self.extra_dirs.get(base_dir)
            assert base
            return os.path.join(base, rel_path)

        if not dir_only:
            rel_path = os.path.join(rel_path, alt_name if alt_name else f"dataset_{object_id}.dat")

        if in_cache:
            return self._get_cache_path(rel_path)

        return rel_path

    def _get_cache_path(self, rel_path: str) -> str:
        return os.path.abspath(os.path.join(self.staging_path, rel_path))

    def _in_cache(self, rel_path: str) -> bool:
        """Check if the given dataset is in the local cache and return True if so."""
        cache_path = self._get_cache_path(rel_path)
        return os.path.exists(cache_path)

    def _pull_into_cache(self, rel_path) -> bool:
        ipt_timer = ExecutionTimer()
        # Ensure the cache directory structure exists (e.g., dataset_#_files/)
        rel_path_dir = os.path.dirname(rel_path)
        if not os.path.exists(self._get_cache_path(rel_path_dir)):
            os.makedirs(self._get_cache_path(rel_path_dir), exist_ok=True)
        # Now pull in the file
        file_ok = self._download(rel_path)
        fix_permissions(self.config, self._get_cache_path(rel_path_dir))
        log.debug("_pull_into_cache: %s\n\n\n\n\n\n", ipt_timer)
        return file_ok

    def _get_data(self, obj, start=0, count=-1, **kwargs):
        rel_path = self._construct_path(obj, **kwargs)
        # Check cache first and get file if not there
        if not self._in_cache(rel_path):
            self._pull_into_cache(rel_path)
        # Read the file content from cache
        data_file = open(self._get_cache_path(rel_path))
        data_file.seek(start)
        content = data_file.read(count)
        data_file.close()
        return content

    def _exists(self, obj, **kwargs):
        in_cache = exists_remotely = False
        rel_path = self._construct_path(obj, **kwargs)
        dir_only = kwargs.get("dir_only", False)
        base_dir = kwargs.get("base_dir", None)

        # check job work directory stuff early to skip API hits.
        if dir_only and base_dir:
            if not os.path.exists(rel_path):
                os.makedirs(rel_path, exist_ok=True)
            return True

        in_cache = self._in_cache(rel_path)
        exists_remotely = self._exists_remotely(rel_path)
        dir_only = kwargs.get("dir_only", False)
        base_dir = kwargs.get("base_dir", None)
        if dir_only:
            if in_cache or exists_remotely:
                return True
            else:
                return False

        # TODO: Sync should probably not be done here. Add this to an async upload stack?
        if in_cache and not exists_remotely:
            self._push_to_os(rel_path, source_file=self._get_cache_path(rel_path))
            return True
        elif exists_remotely:
            return True
        else:
            return False

    def _create(self, obj, **kwargs):
        if not self._exists(obj, **kwargs):
            # Pull out locally used fields
            extra_dir = kwargs.get("extra_dir", None)
            extra_dir_at_root = kwargs.get("extra_dir_at_root", False)
            dir_only = kwargs.get("dir_only", False)
            alt_name = kwargs.get("alt_name", None)

            # Construct hashed path
            rel_path = os.path.join(*directory_hash_id(self._get_object_id(obj)))

            # Optionally append extra_dir
            if extra_dir is not None:
                if extra_dir_at_root:
                    rel_path = os.path.join(extra_dir, rel_path)
                else:
                    rel_path = os.path.join(rel_path, extra_dir)

            # Create given directory in cache
            cache_dir = os.path.join(self.staging_path, rel_path)
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir, exist_ok=True)

            # If instructed, create the dataset in cache & in S3
            if not dir_only:
                rel_path = os.path.join(rel_path, alt_name if alt_name else f"dataset_{self._get_object_id(obj)}.dat")
                open(os.path.join(self.staging_path, rel_path), "w").close()
                self._push_to_os(rel_path, from_string="")
        return self

    def _empty(self, obj, **kwargs):
        if self._exists(obj, **kwargs):
            return self._size(obj, **kwargs) == 0
        else:
            raise ObjectNotFound(f"objectstore.empty, object does not exist: {obj}, kwargs: {kwargs}")

    def _size(self, obj, **kwargs):
        rel_path = self._construct_path(obj, **kwargs)
        if self._in_cache(rel_path):
            try:
                return os.path.getsize(self._get_cache_path(rel_path))
            except OSError as ex:
                log.info("Could not get size of file '%s' in local cache, will try Azure. Error: %s", rel_path, ex)
        elif self._exists_remotely(rel_path):
            return self._get_remote_size(rel_path)
        log.warning("Did not find dataset '%s', returning 0 for size", rel_path)
        return 0

    def _get_filename(self, obj, **kwargs):
        base_dir = kwargs.get("base_dir", None)
        dir_only = kwargs.get("dir_only", False)
        obj_dir = kwargs.get("obj_dir", False)
        sync_cache = kwargs.get("sync_cache", True)

        rel_path = self._construct_path(obj, **kwargs)

        # for JOB_WORK directory
        if base_dir and dir_only and obj_dir:
            return os.path.abspath(rel_path)

        cache_path = self._get_cache_path(rel_path)
        if not sync_cache:
            return cache_path

        # Check if the file exists in the cache first, always pull if file size in cache is zero
        if self._in_cache(rel_path) and (dir_only or os.path.getsize(self._get_cache_path(rel_path)) > 0):
            return cache_path

        # Check if the file exists in persistent storage and, if it does, pull it into cache
        elif self._exists(obj, **kwargs):
            if dir_only:
                self._download_directory_into_cache(rel_path, cache_path)
                return cache_path
            else:
                if self._pull_into_cache(rel_path):
                    return cache_path
        raise ObjectNotFound(f"objectstore.get_filename, no cache_path: {obj}, kwargs: {kwargs}")

    def _download_directory_into_cache(self, rel_path, cache_path):
        # azure, pithos, irod, and cloud did not do this prior to refactoring so I am assuming
        # there is just operations that fail with these object stores,
        # I'm placing a no-op here to match their behavior but we should
        # maybe implement this for those object stores.
        pass

    def _get_remote_size(self, rel_path: str) -> int: ...

    def _exists_remotely(self, rel_path: str) -> bool: ...

    def _push_to_os(self, rel_path, source_file: Optional[str] = None, from_string: Optional[str] = None) -> None: ...

    def _get_object_id(self, obj: Any) -> str: ...

    def _download(self, rel_path: str) -> bool: ...
