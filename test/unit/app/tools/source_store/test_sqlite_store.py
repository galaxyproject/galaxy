"""Unit tests for the SQLite tool source store."""

import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import event
from sqlalchemy.exc import OperationalError

import galaxy.tools.source_store.sqlalchemy as sqlalchemy_store_module
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


def _sqlite_url(path):
    return f"sqlite:///{path}"


def test_store_and_retrieve_round_trip(sqlite_path):
    store = SqliteToolSourceStore(url=_sqlite_url(sqlite_path))
    store.store(_source())
    got = store.get("h1")
    assert got is not None
    assert got.tool_id == "t1"
    assert got.metadata == {"k": "v"}
    assert store.exists("h1")
    assert store.count() == 1


def test_get_by_tool_id_filters_by_version(sqlite_path):
    store = SqliteToolSourceStore(url=_sqlite_url(sqlite_path))
    store.store(_source(hash="h1", tool_id="t1", version="1.0"))
    store.store(_source(hash="h2", tool_id="t1", version="2.0"))
    assert {s.tool_version for s in store.get_by_tool_id("t1")} == {"1.0", "2.0"}
    assert {s.tool_version for s in store.get_by_tool_id("t1", "2.0")} == {"2.0"}


def test_delete_returns_false_for_missing(sqlite_path):
    store = SqliteToolSourceStore(url=_sqlite_url(sqlite_path))
    assert store.delete("nope") is False
    store.store(_source())
    assert store.delete("h1") is True
    assert not store.exists("h1")


def test_index_round_trip(sqlite_path):
    store = SqliteToolSourceStore(url=_sqlite_url(sqlite_path))
    idx = ToolIndex(entries={"t1": ToolIndexEntry(id="t1", name="T1")})
    store.store_index(idx)
    store.invalidate_index_cache()
    loaded = store.load_index()
    assert loaded is not None
    assert "t1" in loaded.entries
    assert loaded.entries["t1"].name == "T1"


def test_update_index_entries_persists_every_entry(sqlite_path):
    store = SqliteToolSourceStore(url=_sqlite_url(sqlite_path))
    store.store_index(ToolIndex(entries={"t1": ToolIndexEntry(id="t1", name="T1")}))

    store.update_index_entries(
        [
            ToolIndexEntry(id="t1", name="T1", data_manager_id="registry/t1"),
            ToolIndexEntry(id="t2", name="T2"),
        ]
    )

    loaded = SqliteToolSourceStore(url=_sqlite_url(sqlite_path)).load_index()
    assert loaded is not None
    assert loaded.entries["t1"].data_manager_id == "registry/t1"
    assert loaded.entries["t2"].name == "T2"


def test_load_index_shares_default_entry_with_version_map(sqlite_path):
    index = ToolIndex()
    index.add_entry(ToolIndexEntry(id="solo", version="1.0", name="Solo"))
    index.add_entry(ToolIndexEntry(id="multi", version="0.1", name="Old"))
    index.add_entry(ToolIndexEntry(id="multi", version="0.2", name="New"))
    SqliteToolSourceStore(url=_sqlite_url(sqlite_path)).store_index(index)

    loaded = SqliteToolSourceStore(url=_sqlite_url(sqlite_path)).load_index()

    assert loaded is not None
    assert loaded.entries_by_version["solo"]["1.0"] is loaded.entries["solo"]
    assert loaded.entries_by_version["multi"]["0.2"] is loaded.entries["multi"]
    old = loaded.get("multi", tool_version="0.1")
    assert old is not None and old is not loaded.entries["multi"]
    assert old.version == "0.1" and old.name == "Old"


def test_load_index_discards_stale_schema(sqlite_path, monkeypatch):
    store = SqliteToolSourceStore(url=_sqlite_url(sqlite_path))
    store.store_index(ToolIndex(entries={"t1": ToolIndexEntry(id="t1", name="T1")}))

    # Simulate a Galaxy upgrade that changed the ToolIndex model: the
    # persisted blob's stamp no longer matches, so the store must report "no
    # index" (triggering a rebuild) rather than load stale/defaulted fields.
    monkeypatch.setattr(sqlalchemy_store_module, "INDEX_SCHEMA_HASH", "post-upgrade-schema-hash")
    fresh = SqliteToolSourceStore(url=_sqlite_url(sqlite_path))
    assert fresh.load_index() is None


def test_read_only_refuses_writes(sqlite_path):
    rw = SqliteToolSourceStore(url=_sqlite_url(sqlite_path))
    rw.store(_source())
    rw.store_index(ToolIndex(entries={"t1": ToolIndexEntry(id="t1", name="T1")}))

    ro = SqliteToolSourceStore(url=_sqlite_url(sqlite_path), read_only=True)
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


def test_get_stats_reports_backend_and_url(sqlite_path):
    store = SqliteToolSourceStore(url=_sqlite_url(sqlite_path))
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


def test_writes_from_threads_are_serialized(sqlite_path):
    store = SqliteToolSourceStore(url=_sqlite_url(sqlite_path))
    open_writes = []
    max_open_writes = 0

    def on_begin(conn):
        nonlocal max_open_writes
        open_writes.append(conn)
        max_open_writes = max(max_open_writes, len(open_writes))

    def on_commit(conn):
        # Holding the transaction open lets an unserialized writer overlap.
        time.sleep(0.05)
        open_writes.remove(conn)

    event.listen(store._engine, "begin", on_begin)
    event.listen(store._engine, "commit", on_commit)

    with ThreadPoolExecutor(4) as pool:
        list(pool.map(lambda i: store.store(_source(hash=f"h{i}", tool_id=f"t{i}")), range(8)))

    assert max_open_writes == 1
    assert store.count() == 8


def test_concurrent_schema_creation_race_is_tolerated(sqlite_path, monkeypatch):
    """Another process creating the schema between the existence check and DDL must not crash."""
    metadata = sqlalchemy_store_module._metadata
    real_create_all = metadata.create_all
    calls = []

    def racing_create_all(bind, *args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            # Simulate a competing process winning the race: tables get created
            # after our existence check, so our DDL hits "already exists".
            real_create_all(bind)
            return real_create_all(bind, checkfirst=False)
        return real_create_all(bind, *args, **kwargs)

    monkeypatch.setattr(metadata, "create_all", racing_create_all)
    store = SqliteToolSourceStore(_sqlite_url(sqlite_path))
    assert len(calls) == 2
    store.store(_source())
    assert store.get("h1") is not None


def test_schema_creation_propagates_unrelated_operational_errors(sqlite_path, monkeypatch):
    def failing_create_all(bind, *args, **kwargs):
        raise OperationalError("CREATE TABLE", {}, Exception("disk I/O error"))

    monkeypatch.setattr(sqlalchemy_store_module._metadata, "create_all", failing_create_all)
    with pytest.raises(OperationalError):
        SqliteToolSourceStore(_sqlite_url(sqlite_path))
