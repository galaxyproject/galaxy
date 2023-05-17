"""
"""
import os
import logging
import time
from typing import (
    List,
    Tuple,
)

from typing_extensions import NamedTuple

from galaxy.util import nice_size

log = logging.getLogger(__name__)


ONE_GIGA_BYTE = 1024 * 1024 * 1024


FileListT = List[Tuple[time.struct_time, str, int]]


class CacheTarget(NamedTuple):
    path: str
    size: int  # cache size in gigabytes
    limit: float  # cache limit as a percent


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
