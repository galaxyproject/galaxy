"""Unit tests for the SQLite tool source store."""

import os
import tempfile

import pytest

from galaxy.tools.source_store import (
    ReadOnlyStoreError,
    StoredToolSource,
)
from galaxy.tools.source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tools.source_store.sqlalchemy import SqlAlchemyToolSourceStore as SqliteToolSourceStore


@pytest.fixture
def sqlite_path():
    with tempfile.TemporaryDirectory() as d:
        yield os.path.join(d, "store.sqlite")


def _source(hash="h1", tool_id="t1", version="1.0"):
    return StoredToolSource(
        hash=hash,
        tool_source_class="XmlToolSource",
        raw_source=f'<tool id="{tool_id}" version="{version}"/>',
        tool_id=tool_id,
        tool_version=version,
        metadata={"k": "v"},
    )


def test_store_and_retrieve_round_trip(sqlite_path):
    store = SqliteToolSourceStore(path=sqlite_path)
    store.store(_source())
    got = store.get("h1")
    assert got is not None
    assert got.tool_id == "t1"
    assert got.metadata == {"k": "v"}
    assert store.exists("h1")
    assert store.count() == 1


def test_get_by_tool_id_filters_by_version(sqlite_path):
    store = SqliteToolSourceStore(path=sqlite_path)
    store.store(_source(hash="h1", tool_id="t1", version="1.0"))
    store.store(_source(hash="h2", tool_id="t1", version="2.0"))
    assert {s.tool_version for s in store.get_by_tool_id("t1")} == {"1.0", "2.0"}
    assert {s.tool_version for s in store.get_by_tool_id("t1", "2.0")} == {"2.0"}


def test_delete_returns_false_for_missing(sqlite_path):
    store = SqliteToolSourceStore(path=sqlite_path)
    assert store.delete("nope") is False
    store.store(_source())
    assert store.delete("h1") is True
    assert not store.exists("h1")


def test_index_round_trip(sqlite_path):
    store = SqliteToolSourceStore(path=sqlite_path)
    idx = ToolIndex(entries={"t1": ToolIndexEntry(id="t1", name="T1")})
    store.store_index(idx)
    store.invalidate_index_cache()
    loaded = store.load_index()
    assert loaded is not None
    assert "t1" in loaded.entries
    assert loaded.entries["t1"].name == "T1"


def test_read_only_refuses_writes(sqlite_path):
    rw = SqliteToolSourceStore(path=sqlite_path)
    rw.store(_source())
    rw.store_index(ToolIndex(entries={"t1": ToolIndexEntry(id="t1", name="T1")}))

    ro = SqliteToolSourceStore(path=sqlite_path, read_only=True)
    assert ro.read_only is True
    fetched = ro.get("h1")
    assert fetched is not None
    assert fetched.tool_id == "t1"
    with pytest.raises(ReadOnlyStoreError):
        ro.store(_source(hash="h2"))
    with pytest.raises(ReadOnlyStoreError):
        ro.delete("h1")
    with pytest.raises(ReadOnlyStoreError):
        ro.store_index(ToolIndex())


def test_read_only_missing_file_raises(tmp_path):
    missing = tmp_path / "nope.sqlite"
    with pytest.raises(FileNotFoundError):
        SqliteToolSourceStore(path=str(missing), read_only=True)


def test_get_stats_reports_backend_and_url(sqlite_path):
    store = SqliteToolSourceStore(path=sqlite_path)
    stats = store.get_stats()
    assert stats["backend"] == "sqlalchemy"
    assert stats["url"].startswith("sqlite:///")
    assert sqlite_path in stats["url"]
    assert stats["read_only"] is False
    assert stats["count"] == 0


def test_url_path_works_with_in_memory_sqlite():
    # Verify the generic url= path works against a non-file backend.
    store = SqliteToolSourceStore(url="sqlite:///:memory:")
    store.store(
        StoredToolSource(
            hash="hmem",
            tool_source_class="XmlToolSource",
            raw_source="<tool/>",
            tool_id="mem",
        )
    )
    fetched = store.get("hmem")
    assert fetched is not None
    assert fetched.tool_id == "mem"


def test_list_source_paths_skips_pathless_rows(sqlite_path):
    store = SqliteToolSourceStore(url=_sqlite_url(sqlite_path))
    with_path = _source(hash="h1", tool_id="t1")
    with_path.source_path = "/tools/a.xml"
    store.store(with_path)
    store.store(_source(hash="h2", tool_id="t2"))
    assert store.list_source_paths() == {"/tools/a.xml"}
