"""Stage 2 of the ObjectStore/FilesSource unification -- the collapse.

``SourceObjectStore`` owns a FilesSource and resolves ``get_filename`` via the source's
``get_local_path``. The same class serves both roles:

- backed by a ``PosixFilesSource`` it is the ``DiskObjectStore`` -- ``get_filename`` returns
  the real backing file (zero copy), no object-store cache;
- backed by a ``CachingFilesSource`` (wrapping an fsspec source) it is the ``S3ObjectStore``
  -- ``get_filename`` returns a cache path populated on demand.

The "disk role" tests below assert parity with the canonical ``DiskObjectStore`` contract
(dataset round-trip, ``store_by=uuid``, ``alt_name``, job-work directories, usage %). See
doc/source/dev/objectstore_filesource_unification.md.
"""

import os

from fsspec.implementations.memory import MemoryFileSystem

from galaxy.objectstore import build_object_store_from_config
from galaxy.objectstore._caching_source import CachingFilesSource
from galaxy.objectstore.source_store import SourceObjectStore
from galaxy.objectstore.unittest_utils import MockConfig
from galaxy.util import directory_hash_id
from ._unification_utils import (
    assert_object_store_round_trip,
    Dataset,
    key,
    memory_files_source,
    posix_files_source,
    remote_file,
)


def _config(tmp_path, **overrides):
    config = MockConfig(str(tmp_path), "unused.yaml", store_by=overrides.pop("store_by", "id"))
    for attr, value in overrides.items():
        setattr(config, attr, value)
    return config


def _make_store(tmp_path, source, **config_overrides):
    return SourceObjectStore(_config(tmp_path, **config_overrides), {}, source)


# --- disk role (posix-backed) ---


def test_disk_role_round_trip_posix(tmp_path):
    remote = tmp_path / "remote"
    remote.mkdir()
    store = _make_store(tmp_path, posix_files_source(remote))
    assert_object_store_round_trip(
        store,
        tmp_path,
        remote_content=lambda i: remote_file(remote, i).read_text(),
        remote_exists=lambda i: remote_file(remote, i).exists(),
    )


def test_disk_role_get_filename_is_zero_copy(tmp_path):
    # Backed by posix, get_filename returns the REAL backing file, not a copy.
    remote = tmp_path / "remote"
    remote.mkdir()
    store = _make_store(tmp_path, posix_files_source(remote))
    ds = Dataset(9)
    src = tmp_path / "s"
    src.write_text("data")
    store.update_from_file(ds, file_name=str(src), create=True)

    assert store.get_filename(ds) == str(remote_file(remote, 9))


def test_disk_role_store_by_uuid(tmp_path):
    remote = tmp_path / "remote"
    remote.mkdir()
    store = _make_store(tmp_path, posix_files_source(remote), store_by="uuid")
    ds = Dataset(3)
    src = tmp_path / "s"
    src.write_text("hi")
    store.update_from_file(ds, file_name=str(src), create=True)

    assert store.exists(ds)
    assert store.size(ds) == 2
    rel = os.path.join(*directory_hash_id(ds.uuid), f"dataset_{ds.uuid}.dat")
    assert (remote / rel).read_text() == "hi"


def test_disk_role_alt_name(tmp_path):
    remote = tmp_path / "remote"
    remote.mkdir()
    store = _make_store(tmp_path, posix_files_source(remote))
    ds = Dataset(3)
    src = tmp_path / "s"
    src.write_text("alt")
    store.update_from_file(ds, file_name=str(src), create=True, alt_name="custom.txt")

    assert store.exists(ds, alt_name="custom.txt")
    fname = store.get_filename(ds, alt_name="custom.txt")
    assert fname.endswith("custom.txt")
    with open(fname) as fh:
        assert fh.read() == "alt"


def test_disk_role_store_usage_percent(tmp_path):
    remote = tmp_path / "remote"
    remote.mkdir()
    store = _make_store(tmp_path, posix_files_source(remote))
    pct = store.get_store_usage_percent()
    assert 0.0 < pct < 100.0


def test_disk_role_job_work_directory(tmp_path):
    # job_work / temp are always-local scratch dirs, independent of the dataset source.
    remote = tmp_path / "datasets"
    remote.mkdir()
    jobs = tmp_path / "jobs"
    jobs.mkdir()
    store = _make_store(tmp_path, posix_files_source(remote), jobs_directory=str(jobs))
    job = Dataset(42)

    jw_kwargs = dict(base_dir="job_work", dir_only=True, obj_dir=True)
    assert not store.exists(job, **jw_kwargs)

    store.create(job, **jw_kwargs)
    assert store.exists(job, **jw_kwargs)

    work_dir = store.get_filename(job, **jw_kwargs)
    assert work_dir.startswith(str(jobs))  # local, not the dataset source
    assert os.path.isdir(work_dir)

    assert store.delete(job, entire_dir=True, **jw_kwargs)
    assert not store.exists(job, **jw_kwargs)


# --- cloud role (caching-source-backed) ---


def test_cloud_role_round_trip_caching_memory(clean_memory_fs, tmp_path):
    source = CachingFilesSource(memory_files_source(), staging_path=str(tmp_path / "srccache"))
    store = _make_store(tmp_path, source)
    assert_object_store_round_trip(
        store,
        tmp_path,
        remote_content=lambda i: MemoryFileSystem().cat(key(i)).decode(),
        remote_exists=lambda i: MemoryFileSystem().exists(key(i)),
    )


def test_cloud_role_get_filename_is_cache_path(clean_memory_fs, tmp_path):
    # Backed by a caching source, get_filename returns a cache path (not a backing path).
    cache = tmp_path / "srccache"
    source = CachingFilesSource(memory_files_source(), staging_path=str(cache))
    store = _make_store(tmp_path, source)
    ds = Dataset(9)
    src = tmp_path / "s"
    src.write_text("data")
    store.update_from_file(ds, file_name=str(src), create=True)

    fname = store.get_filename(ds)
    assert fname.startswith(str(cache))
    with open(fname) as fh:
        assert fh.read() == "data"


# --- built from config (build_object_store_from_config) ---


def test_build_from_config_posix_disk_role(tmp_path):
    remote = tmp_path / "remote"
    remote.mkdir()
    config_dict = {
        "type": "source",
        "files_source": {"type": "posix", "root": str(remote), "writable": True},
    }
    store = build_object_store_from_config(_config(tmp_path), config_dict=config_dict)
    assert isinstance(store, SourceObjectStore)
    assert_object_store_round_trip(
        store,
        tmp_path,
        remote_content=lambda i: remote_file(remote, i).read_text(),
        remote_exists=lambda i: remote_file(remote, i).exists(),
    )


def test_build_from_config_caching_cloud_role(clean_memory_fs, tmp_path):
    config_dict = {
        "type": "source",
        "files_source": {"type": "memory", "writable": True},
        "cache": {"path": str(tmp_path / "cache")},
    }
    store = build_object_store_from_config(_config(tmp_path), config_dict=config_dict)
    assert isinstance(store, SourceObjectStore)
    assert_object_store_round_trip(
        store,
        tmp_path,
        remote_content=lambda i: MemoryFileSystem().cat(key(i)).decode(),
        remote_exists=lambda i: MemoryFileSystem().exists(key(i)),
    )
