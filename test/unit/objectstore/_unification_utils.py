"""Shared helpers for the ObjectStore/FilesSource unification tests (Stages 1 & 2).

See doc/source/dev/objectstore_filesource_unification.md.
"""

import os
from uuid import uuid4

import pytest

from galaxy.util import directory_hash_id

# These helpers need galaxy-files + fsspec; skip cleanly when the galaxy-objectstore package
# is tested in isolation without them (this module is collected directly by pytest).
pytest.importorskip("fsspec")
pytest.importorskip("galaxy.files")

from galaxy.files.plugins import FileSourcePluginsConfig  # noqa: E402  (after importorskip)
from galaxy.files.unittest_utils import TestConfiguredFileSources  # noqa: E402  (after importorskip)


class Dataset:
    def __init__(self, id):
        self.id = id
        self.object_store_id = None
        self.uuid = uuid4()
        self.tags = []


def key(dataset_id):
    """The relative key an id-addressed object store constructs for a dataset."""
    return os.path.join(*directory_hash_id(dataset_id), f"dataset_{dataset_id}.dat")


def remote_file(remote, dataset_id):
    return remote / key(dataset_id)


def posix_files_source(root):
    plugin = {"type": "posix", "root": str(root), "writable": True}
    sources = TestConfiguredFileSources(FileSourcePluginsConfig(), {"test1": plugin}, str(root))
    return sources.find_best_match("gxfiles://test1/")


def memory_files_source():
    plugin = {"type": "memory", "writable": True}
    sources = TestConfiguredFileSources(FileSourcePluginsConfig(), {"mem1": plugin}, None)
    return sources.find_best_match("memory://mem1/")


def assert_object_store_round_trip(store, tmp_path, remote_content, remote_exists):
    """Full lifecycle through an object store, verifying the backing store directly.

    ``remote_content(id) -> str`` and ``remote_exists(id) -> bool`` read the backend (not the
    cache), so the assertions hold for any transport or source.
    """
    # Absent dataset does not exist.
    assert not store.exists(Dataset(1))

    # Empty dataset created via create().
    empty = Dataset(2)
    store.create(empty)
    assert store.exists(empty)
    assert store.empty(empty)

    # Writing a dataset lands the bytes in the backend and makes it retrievable.
    ds = Dataset(3)
    src = tmp_path / "src.txt"
    src.write_text("Hello World!")
    store.update_from_file(ds, file_name=str(src), create=True)

    assert store.exists(ds)
    assert not store.empty(ds)
    assert store.size(ds) == len("Hello World!")

    # The backend (not just the cache) received the bytes.
    assert remote_content(3) == "Hello World!"

    # get_filename yields a real, readable local path.
    fname = store.get_filename(ds)
    assert os.path.exists(fname)
    with open(fname) as fh:
        assert fh.read() == "Hello World!"

    # Byte-range reads are served from the resolved local path.
    assert store.get_data(ds, start=1, count=6) == "ello W"

    # Deleting removes the object from the backend as well.
    assert store.delete(ds)
    assert not store.exists(ds)
    assert not remote_exists(3)
