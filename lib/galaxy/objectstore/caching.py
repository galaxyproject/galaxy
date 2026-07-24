""" """

import hashlib
import logging
import os
import threading
import time
from math import inf
from uuid import UUID

from typing_extensions import NamedTuple

from galaxy.util import (
    nice_size,
    string_as_bool,
)
from galaxy.util.sleeper import Sleeper

log = logging.getLogger(__name__)


ONE_GIGA_BYTE = 1024 * 1024 * 1024


FileListT = list[tuple[time.struct_time, str, int]]

#: The type of an object identifier used for cache shard selection.
#: Can be a numeric id (``store_by="id"``) or a UUID / string
#: (``store_by="uuid"``).
ObjectId = int | UUID | str


class CacheTarget(NamedTuple):
    path: str
    size: float  # cache size in gigabytes
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


class CacheShard(NamedTuple):
    path: str
    weight: int
    size: float


def parse_cache_dirs_from_xml(cache_element) -> list[dict] | None:
    """Parse <dirs><dir .../></dirs> from a cache XML element.

    Returns a list of dicts with keys ``path``, ``weight``, ``size``
    (size may be ``None``), or ``None`` if no ``<dirs>`` element is present.
    """
    dirs_els = cache_element.findall("dirs")
    if not dirs_els:
        return None
    dir_els = dirs_els[0].findall("dir")
    if not dir_els:
        return None
    return [
        {
            "path": d.get("path"),
            "weight": int(d.get("weight", 1)),
            "size": float(d.get("size", -1)) if d.get("size") is not None else None,
        }
        for d in dir_els
    ]


class CacheShardManager:
    def __init__(self, shards: list[CacheShard]):
        if not shards:
            raise ValueError("CacheShardManager requires at least one shard")
        self.shards = shards
        total_weight = sum(s.weight for s in shards)
        self._weighted_index: list[tuple[int, CacheShard]] = []
        cumulative = 0
        for shard in shards:
            cumulative += shard.weight
            self._weighted_index.append((cumulative, shard))
        self._total_weight = total_weight

    def _select_shard(self, object_id: ObjectId) -> CacheShard:
        digest = hashlib.sha256(str(object_id).encode()).digest()
        hash_value = int.from_bytes(digest, "big")
        point = hash_value % self._total_weight
        for cumulative, shard in self._weighted_index:
            if point < cumulative:
                return shard
        return self.shards[-1]

    def get_cache_path(self, object_id: ObjectId, rel_path: str) -> str:
        shard = self._select_shard(object_id)
        return os.path.abspath(os.path.join(shard.path, rel_path))

    def get_cache_target(self, object_id: ObjectId) -> CacheTarget:
        shard = self._select_shard(object_id)
        return CacheTarget(shard.path, shard.size, 0.9)

    @property
    def paths(self) -> list[str]:
        return [s.path for s in self.shards]

    @property
    def cache_targets(self) -> list[CacheTarget]:
        return [CacheTarget(s.path, s.size, 0.9) for s in self.shards]

    def to_config_dict(self) -> dict:
        """Serialize shard config for backend ``to_dict`` / reconstruction.

        Emits ``dirs`` when there are multiple shards, otherwise the legacy
        single ``path`` / ``size`` keys.  ``weight`` is intentionally omitted
        for the single-shard case because it is meaningless with only one shard.
        """
        if len(self.shards) == 1:
            s = self.shards[0]
            return {"path": s.path, "size": s.size}
        return {
            "dirs": [{"path": s.path, "weight": s.weight, "size": s.size} for s in self.shards],
        }

    @classmethod
    def from_config(cls, cache_dict: dict, config) -> "CacheShardManager":
        default_size = cache_dict.get("size") or config.object_store_cache_size
        default_path = cache_dict.get("path") or config.object_store_cache_path

        dirs = cache_dict.get("dirs")
        if dirs:
            shards: list[CacheShard] = []
            for d in dirs:
                path = d.get("path")
                if not path:
                    continue
                weight = d.get("weight", 1)
                if weight <= 0:
                    continue
                size = d.get("size")
                if size is None:
                    size = default_size
                shards.append(CacheShard(path=path, weight=weight, size=size))
            if shards:
                return cls(shards)

        return cls([CacheShard(path=default_path, weight=1, size=default_size)])


def check_caches(targets: list[CacheTarget]):
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
    if total_size > (cache_limit := cache_size_in_gb * cache_target.limit):
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


def _get_cache_size_files(cache_path) -> tuple[int, FileListT]:
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

        dirs = parse_cache_dirs_from_xml(c_xml)
        if dirs:
            cache_dict["dirs"] = dirs
    else:
        cache_dict = {}
    return cache_dict


def enable_cache_monitor(config, config_dict) -> tuple[bool, int]:
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
    def __init__(self, cache_targets: list[CacheTarget], interval: int = 30, initial_sleep: int | None = 2):
        # This Event object is initialized to False
        # It is set to True in shutdown(), causing
        # the cache monitor thread to return/terminate
        self.stop_cache_monitor_event = threading.Event()
        # Helper for interruptable sleep
        self.sleeper = Sleeper()

        self.cache_targets = cache_targets
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
            check_caches(self.cache_targets)
            self.sleeper.sleep(self.interval)

    def shutdown(self):
        # Set the event object so the cache monitor thread terminates
        self.stop_cache_monitor_event.set()

        # wake up from sleeping
        self.sleeper.wake()

        # Wait for the cache monitor thread to join before ending
        self.cache_monitor_thread.join(5)
