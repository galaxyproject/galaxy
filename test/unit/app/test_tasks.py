from typing import List

from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.celery.tasks import clean_object_store_caches
from galaxy.objectstore import BaseObjectStore
from galaxy.objectstore.caching import CacheTarget


class MockObjectStore:
    def __init__(self, cache_targets: List[CacheTarget]):
        self._cache_targets = cache_targets

    def cache_targets(self) -> List[CacheTarget]:
        return self._cache_targets


def test_clean_object_store_caches(tmp_path):
    container = MockApp()
    cache_targets: List[CacheTarget] = []
    container[BaseObjectStore] = MockObjectStore(cache_targets)  # type: ignore[assignment]

    # similar code used in object store unit tests
    cache_dir = tmp_path
    path = cache_dir / "a_file_0"
    path.write_text("this is an example file")

    # works fine on an empty list of cache targets...
    clean_object_store_caches()

    assert path.exists()

    # place the file in mock object store's cache targets and
    # run the task again and the above file should be gone.
    cache_targets.append(CacheTarget(cache_dir, 1, 0.000000001))
    # works fine on an empty list of cache targets...
    clean_object_store_caches()

    assert not path.exists()
