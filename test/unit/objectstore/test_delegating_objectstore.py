"""Stage 1 of the ObjectStore/FilesSource unification.

These tests prove that a CachingConcreteObjectStore's *transport* (the whole-file,
key-addressed I/O below its cache) can be satisfied by an injected object, with the
entire cache layer left untouched:

- ``test_round_trip_local_transport`` uses a plain local-filesystem transport.
- ``test_round_trip_files_source_transport`` uses a *real* ``PosixFilesSource`` wrapped
  as a transport -- the central thesis of the proposal, that the object store's transport
  seam *is* the FilesSource contract.
- ``test_round_trip_fsspec_memory_transport`` / ``test_fsspec_size_served_from_cold_cache``
  do the same through an fsspec-backed source (``MemoryFilesSource``), exercising the
  ``FsspecFilesSource`` base-class ``exists``/``size``/``remove`` defaults that every cloud
  source (s3fs, azure, gcs, ...) inherits. A real S3-behind-moto run is a gated follow-up.

A local directory or the in-process memory filesystem stands in for a remote store, so no
cloud credentials are needed. See doc/source/dev/objectstore_filesource_unification.md.
"""

import shutil

from fsspec.implementations.memory import MemoryFileSystem

from galaxy.objectstore._transport import (
    FilesSourceTransport,
    LocalTransport,
)
from galaxy.objectstore.delegating import DelegatingObjectStore
from galaxy.objectstore.unittest_utils import MockConfig
from ._unification_utils import (
    assert_object_store_round_trip,
    Dataset,
    key,
    memory_files_source,
    posix_files_source,
    remote_file,
)


def _make_store(tmp_path, transport):
    config = MockConfig(str(tmp_path), "unused.yaml")
    config_dict = {"cache": {"path": str(tmp_path / "cache")}}
    return DelegatingObjectStore(config, config_dict, transport=transport)


def test_round_trip_local_transport(tmp_path):
    remote = tmp_path / "remote"
    remote.mkdir()
    store = _make_store(tmp_path, LocalTransport(str(remote)))
    assert_object_store_round_trip(
        store,
        tmp_path,
        remote_content=lambda i: remote_file(remote, i).read_text(),
        remote_exists=lambda i: remote_file(remote, i).exists(),
    )


def test_round_trip_files_source_transport(tmp_path):
    remote = tmp_path / "remote"
    remote.mkdir()
    store = _make_store(tmp_path, FilesSourceTransport(posix_files_source(remote)))
    assert_object_store_round_trip(
        store,
        tmp_path,
        remote_content=lambda i: remote_file(remote, i).read_text(),
        remote_exists=lambda i: remote_file(remote, i).exists(),
    )


def test_round_trip_fsspec_memory_transport(clean_memory_fs, tmp_path):
    store = _make_store(tmp_path, FilesSourceTransport(memory_files_source()))
    assert_object_store_round_trip(
        store,
        tmp_path,
        remote_content=lambda i: MemoryFileSystem().cat(key(i)).decode(),
        remote_exists=lambda i: MemoryFileSystem().exists(key(i)),
    )


def test_fsspec_size_served_from_cold_cache(clean_memory_fs, tmp_path):
    # With a cold cache, exists/size/get_filename must be served from the fsspec backend,
    # exercising FsspecFilesSource._exists / _size / _realize_to.
    store = _make_store(tmp_path, FilesSourceTransport(memory_files_source()))
    ds = Dataset(5)
    src = tmp_path / "s"
    src.write_text("12345678")
    store.update_from_file(ds, file_name=str(src), create=True)

    shutil.rmtree(tmp_path / "cache")  # evict everything from the local cache

    assert store.exists(ds)  # -> source.exists
    assert store.size(ds) == 8  # -> source.size (remote branch)
    with open(store.get_filename(ds)) as fh:  # -> source.realize_to + caching-allowed size check
        assert fh.read() == "12345678"


def test_get_filename_pulls_from_remote_into_cache(tmp_path):
    # A dataset present only in the remote is pulled into the local cache on demand.
    remote = tmp_path / "remote"
    rf = remote_file(remote, 7)
    rf.parent.mkdir(parents=True)
    rf.write_text("remote-only")

    store = _make_store(tmp_path, LocalTransport(str(remote)))
    ds = Dataset(7)

    assert store.exists(ds)
    fname = store.get_filename(ds)
    # It returns the cache path, not the remote path...
    assert fname.startswith(str(tmp_path / "cache"))
    # ...populated from the transport.
    with open(fname) as fh:
        assert fh.read() == "remote-only"
