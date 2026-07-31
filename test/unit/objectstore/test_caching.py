import os
from unittest.mock import MagicMock

import pytest

from galaxy.objectstore._caching_base import CachingConcreteObjectStore
from galaxy.objectstore.caching import (
    CacheShard,
    CacheShardManager,
)


class FakeConfig:
    def __init__(self, cache_path=None, cache_size=-1):
        self.object_store_cache_path = cache_path or "/tmp/default_cache"
        self.object_store_cache_size = cache_size


def make_shards(paths, weights=None, sizes=None):
    weights = weights or [1] * len(paths)
    sizes = sizes or [-1] * len(paths)
    return [CacheShard(path=p, weight=w, size=s) for p, w, s in zip(paths, weights, sizes)]


def _is_in_shard(path: str, shard_path: str) -> bool:
    """True if *path* is *shard_path* itself or a file/directory inside it."""
    return path == shard_path or path.startswith(shard_path + os.sep)


def _shard_root(path: str, shard_paths: list[str]) -> str:
    """Return the shard root that *path* belongs to."""
    return next(sp for sp in shard_paths if _is_in_shard(path, sp))


def test_multi_shard_manager():
    shards = make_shards(["/fast", "/slow"], weights=[3, 1], sizes=[500, 200])
    mgr = CacheShardManager(shards)
    assert len(mgr.shards) == 2
    assert mgr.paths == ["/fast", "/slow"]
    assert len(mgr.cache_targets) == 2
    assert mgr.cache_targets[0].path == "/fast"
    assert mgr.cache_targets[0].size == 500
    assert mgr.cache_targets[1].path == "/slow"
    assert mgr.cache_targets[1].size == 200


def test_same_shard_for_same_object_id():
    shards = make_shards(["/a", "/b", "/c"], weights=[2, 1, 1])
    mgr = CacheShardManager(shards)
    obj_id = 12345
    main_path = mgr.get_cache_path(obj_id, "000/dataset_12345.dat")
    extra_path = mgr.get_cache_path(obj_id, "000/dataset_12345_files/extra.txt")
    shard_paths = mgr.paths

    # The main dataset file and its extra_files must resolve to the same shard
    # because they share the same object_id.
    assert _shard_root(main_path, shard_paths) == _shard_root(extra_path, shard_paths)


def test_metadata_file_may_land_on_different_shard():
    """MetadataFile has its own id space — _get_object_id returns the
    MetadataFile's id, not the Dataset's id.  With multiple shards the
    metadata file may land on a different shard than the dataset.

    This test verifies that the shard selection is purely a function of
    the object_id passed in — different ids can (and often do) map to
    different shards.
    """
    shards = make_shards(["/a", "/b"], weights=[1, 1])
    mgr = CacheShardManager(shards)
    shard_paths = mgr.paths

    # Find a dataset id and a metadata id that land on different shards.
    # With 2 equal-weight shards this happens ~50% of the time.
    found_divergence = False
    for dataset_id in range(1000):
        dataset_path = mgr.get_cache_path(dataset_id, "000/dataset.dat")
        dataset_shard = _shard_root(dataset_path, shard_paths)
        for metadata_id in range(1000):
            metadata_path = mgr.get_cache_path(metadata_id, "000/metadata.dat")
            metadata_shard = _shard_root(metadata_path, shard_paths)
            if dataset_shard != metadata_shard:
                found_divergence = True
                break
        if found_divergence:
            break

    assert found_divergence, "Expected at least one dataset/metadata pair to land on different shards"


def test_weight_distribution():
    shards = make_shards(["/a", "/b"], weights=[3, 1])
    mgr = CacheShardManager(shards)
    counts = {"a": 0, "b": 0}
    n = 10000
    for i in range(n):
        path = mgr.get_cache_path(i, "file.dat")
        if _is_in_shard(path, "/a"):
            counts["a"] += 1
        else:
            counts["b"] += 1
    ratio_a = counts["a"] / n
    assert 0.70 < ratio_a < 0.80, f"Expected ~75% for weight 3, got {ratio_a}"


def test_from_config_legacy_single_path():
    cache_dict = {"path": "/cache", "size": 100}
    config = FakeConfig()
    mgr = CacheShardManager.from_config(cache_dict, config)
    assert len(mgr.shards) == 1
    assert mgr.shards[0].path == "/cache"
    assert mgr.shards[0].size == 100
    assert mgr.shards[0].weight == 1


def test_from_config_multi_dir():
    cache_dict = {
        "dirs": [
            {"path": "/fast", "weight": 3, "size": 500},
            {"path": "/slow", "weight": 1, "size": 200},
        ],
        "size": 100,
    }
    config = FakeConfig()
    mgr = CacheShardManager.from_config(cache_dict, config)
    assert len(mgr.shards) == 2
    assert mgr.shards[0].path == "/fast"
    assert mgr.shards[0].weight == 3
    assert mgr.shards[0].size == 500
    assert mgr.shards[1].path == "/slow"
    assert mgr.shards[1].weight == 1
    assert mgr.shards[1].size == 200


@pytest.mark.parametrize(
    "cache_dict, config_size, expected_paths, expected_sizes",
    [
        # Empty dirs → fallback to single path
        ({"dirs": [], "path": "/cache", "size": 100}, -1, ["/cache"], [100]),
        # All invalid entries → fallback to single path
        (
            {
                "dirs": [{"path": None}, {"path": "/zero", "weight": 0}],
                "path": "/fallback",
                "size": 100,
            },
            -1,
            ["/fallback"],
            [100],
        ),
        # Empty dict → config defaults
        ({}, 10, ["/default"], [10]),
        # Invalid entries filtered, valid ones kept
        (
            {
                "dirs": [
                    {"path": "/valid", "weight": 2, "size": 300},
                    {"path": None, "weight": 1},
                    {"path": "/zero_weight", "weight": 0, "size": 100},
                    {"path": "/negative", "weight": -1, "size": 100},
                ],
                "path": "/fallback",
                "size": 100,
            },
            -1,
            ["/valid"],
            [300],
        ),
        # Size fallback: per-dir missing → top-level size
        (
            {
                "dirs": [
                    {"path": "/a", "weight": 1},
                    {"path": "/b", "weight": 1, "size": 200},
                ],
                "size": 100,
            },
            -1,
            ["/a", "/b"],
            [100, 200],
        ),
        # Size fallback: per-dir + top-level missing → config default
        (
            {"dirs": [{"path": "/a", "weight": 1}]},
            50,
            ["/a"],
            [50],
        ),
    ],
)
def test_from_config_fallbacks(cache_dict, config_size, expected_paths, expected_sizes):
    config = FakeConfig(cache_path="/default", cache_size=config_size)
    mgr = CacheShardManager.from_config(cache_dict, config)
    assert mgr.paths == expected_paths
    assert [s.size for s in mgr.shards] == expected_sizes


def test_cache_targets_sizes():
    shards = make_shards(["/a", "/b"], sizes=[100, 200])
    mgr = CacheShardManager(shards)
    targets = mgr.cache_targets
    assert targets[0].size == 100
    assert targets[1].size == 200
    assert targets[0].path == "/a"
    assert targets[1].path == "/b"


def test_get_cache_target():
    shards = make_shards(["/a", "/b"], sizes=[100, 200])
    mgr = CacheShardManager(shards)
    target = mgr.get_cache_target(42)
    assert target.path in ["/a", "/b"]
    assert target.size in [100, 200]
    assert target.limit == 0.9


def test_empty_shards_raises():
    with pytest.raises(ValueError, match="at least one shard"):
        CacheShardManager([])


class StubCachingBackend(CachingConcreteObjectStore):
    def __init__(self, cache_shards):
        self._cache_shards = cache_shards
        self.config = MagicMock()
        self.config.umask = 0o002
        self.config.gid = -1
        self.cache_updated_data = True
        self.store_by = "id"
        self.extra_dirs = {}

    def _get_object_id(self, obj):
        return obj

    def _get_remote_size(self, rel_path):
        return 0

    def _exists_remotely(self, rel_path):
        return False

    def _download(self, rel_path, *, object_id):
        return False

    def _push_string_to_path(self, rel_path, from_string):
        return True

    def _push_file_to_path(self, rel_path, source_file):
        return True

    def _delete_existing_remote(self, rel_path):
        return True

    def _delete_remote_all(self, rel_path):
        return True


@pytest.fixture
def two_dir_cache(tmp_path):
    cache_a = tmp_path / "cache_a"
    cache_b = tmp_path / "cache_b"
    cache_a.mkdir()
    cache_b.mkdir()
    config = FakeConfig(cache_path=str(cache_a), cache_size=-1)
    cache_dict = {
        "dirs": [
            {"path": str(cache_a), "weight": 1, "size": -1},
            {"path": str(cache_b), "weight": 1, "size": -1},
        ],
    }
    mgr = CacheShardManager.from_config(cache_dict, config)
    return StubCachingBackend(mgr), str(cache_a), str(cache_b)


def test_backend_cache_targets(two_dir_cache):
    backend, cache_a, cache_b = two_dir_cache
    targets = backend.cache_targets()
    assert len(targets) == 2
    paths = {t.path for t in targets}
    assert paths == {cache_a, cache_b}


def test_backend_first_shard_properties(two_dir_cache):
    backend, cache_a, cache_b = two_dir_cache
    assert backend.staging_path == cache_a
    assert backend.cache_target.path == cache_a


def test_backend_get_filename_no_sync(two_dir_cache):
    backend, cache_a, cache_b = two_dir_cache
    obj_id = 42
    cache_path = backend._get_cache_path("000/dataset_42.dat", object_id=obj_id)
    assert _is_in_shard(cache_path, cache_a) or _is_in_shard(cache_path, cache_b)


def test_backend_create_and_delete(two_dir_cache):
    backend, cache_a, cache_b = two_dir_cache
    obj_id = 99
    obj = MagicMock()
    obj.id = obj_id

    backend._create(obj)

    filename = backend._get_filename(obj, sync_cache=False)
    assert os.path.exists(filename)

    backend._delete(obj)
    assert not os.path.exists(filename)


def test_backend_update_and_size(two_dir_cache, tmp_path):
    backend, cache_a, cache_b = two_dir_cache
    obj = MagicMock()
    obj.id = 77

    src = tmp_path / "source.txt"
    src.write_text("hello world")

    backend._create(obj)
    backend._update_from_file(obj, file_name=str(src), create=True)

    filename = backend._get_filename(obj, sync_cache=False)
    assert os.path.exists(filename)
    with open(filename) as f:
        assert f.read() == "hello world"
    assert backend._size(obj) == len("hello world")

    backend._delete(obj)


def test_backend_pull_into_cache_writes_to_correct_shard(two_dir_cache):
    """_pull_into_cache should download the file to the shard selected for that object_id."""
    backend, cache_a, cache_b = two_dir_cache
    obj_id = 42
    obj = MagicMock()
    obj.id = obj_id

    # Determine which shard this object_id maps to
    expected_path = backend._get_cache_path("000/dataset_42.dat", object_id=obj_id)
    expected_shard = cache_a if _is_in_shard(expected_path, cache_a) else cache_b

    # Patch _download to write a file instead of returning False
    def fake_download(rel_path, *, object_id):
        cache_path = backend._get_cache_path(rel_path, object_id)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w") as f:
            f.write("downloaded content")
        return True

    backend._download = fake_download

    result = backend._pull_into_cache("000/dataset_42.dat", object_id=obj_id)
    assert result is True
    assert os.path.exists(expected_path)
    assert _is_in_shard(expected_path, expected_shard)
    with open(expected_path) as f:
        assert f.read() == "downloaded content"

    # Cleanup
    backend._delete(obj)
