"""
"""

import logging
import os
import threading
import time
from math import inf
from typing import (
    List,
    Optional,
    Tuple,
)

from typing_extensions import NamedTuple

from galaxy.util import (
    nice_size,
    string_as_bool,
)
from galaxy.util.sleeper import Sleeper

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
