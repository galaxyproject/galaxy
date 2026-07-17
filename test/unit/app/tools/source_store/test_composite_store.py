"""Unit tests for CompositeToolSourceStore + merged ToolIndex."""

import os
import tempfile

import pytest

from galaxy.tools.source_store import StoredToolSource
from galaxy.tools.cached_toolbox import CachedToolBox
from galaxy.tools.source_store.composite import CompositeToolSourceStore
from galaxy.tools.source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tools.source_store.sqlalchemy import SqlAlchemyToolSourceStore as SqliteToolSourceStore
from galaxy.tools.source_store.unavailable import UnavailableToolSourceStore


@pytest.fixture
def two_paths():
    with tempfile.TemporaryDirectory() as d:
        yield os.path.join(d, "a.sqlite"), os.path.join(d, "b.sqlite")


def _src(hash, tool_id="t", version="1"):
    return StoredToolSource(
        hash=hash,
        tool_source_class="XmlToolSource",
        raw_source=f'<tool id="{tool_id}" version="{version}"/>',
        tool_id=tool_id,
        tool_version=version,
    )


def _sqlite_url(path):
    return f"sqlite:///{path}"


def test_priority_order_first_hit_wins(two_paths):
    pa, pb = two_paths
    a = SqliteToolSourceStore(url=_sqlite_url(pa))
    b = SqliteToolSourceStore(url=_sqlite_url(pb))
    # Same hash, different tool_id payloads, to prove which member answered.
    a.store(_src("dup", tool_id="from_a"))
    b.store(_src("dup", tool_id="from_b"))
    composite = CompositeToolSourceStore(members=[("a", a), ("b", b)], default="b")
    got = composite.get("dup")
    assert got is not None
    assert got.tool_id == "from_a"


def test_writes_go_to_default(two_paths):
    pa, pb = two_paths
    a = SqliteToolSourceStore(url=_sqlite_url(pa))
    b = SqliteToolSourceStore(url=_sqlite_url(pb))
    composite = CompositeToolSourceStore(members=[("a", a), ("b", b)], default="b")
    composite.store(_src("h1"))
    assert b.exists("h1")
    assert not a.exists("h1")


def test_default_must_not_be_read_only(two_paths):
    pa, pb = two_paths
    rw = SqliteToolSourceStore(url=_sqlite_url(pa))
    rw.store(_src("seed"))  # so the file exists
    ro = SqliteToolSourceStore(url=_sqlite_url(pa), read_only=True)
    with pytest.raises(ValueError):
        CompositeToolSourceStore(members=[("ro", ro), ("rw", rw)], default="ro")


def test_list_all_dedupes_across_members(two_paths):
    pa, pb = two_paths
    a = SqliteToolSourceStore(url=_sqlite_url(pa))
    b = SqliteToolSourceStore(url=_sqlite_url(pb))
    a.store(_src("h1"))
    a.store(_src("dup"))
    b.store(_src("dup"))
    b.store(_src("h2"))
    composite = CompositeToolSourceStore(members=[("a", a), ("b", b)], default="b")
    assert sorted(composite.list_all()) == ["dup", "h1", "h2"]
    assert composite.count() == 3


def test_load_index_merges_and_dedupes(two_paths):
    pa, pb = two_paths
    a = SqliteToolSourceStore(url=_sqlite_url(pa))
    b = SqliteToolSourceStore(url=_sqlite_url(pb))
    a.store_index(
        ToolIndex(
            entries={
                "shared": ToolIndexEntry(id="shared", name="from_a"),
                "only_a": ToolIndexEntry(id="only_a", name="A only"),
            }
        )
    )
    b.store_index(
        ToolIndex(
            entries={
                "shared": ToolIndexEntry(id="shared", name="from_b"),
                "only_b": ToolIndexEntry(id="only_b", name="B only"),
            }
        )
    )
    composite = CompositeToolSourceStore(members=[("a", a), ("b", b)], default="b")
    merged = composite.load_index()
    assert merged is not None
    assert set(merged.entries.keys()) == {"shared", "only_a", "only_b"}
    # Earlier member wins on collision.
    assert merged.entries["shared"].name == "from_a"


def test_load_index_returns_none_when_no_member_has_one(two_paths):
    pa, pb = two_paths
    a = SqliteToolSourceStore(url=_sqlite_url(pa))
    b = SqliteToolSourceStore(url=_sqlite_url(pb))
    composite = CompositeToolSourceStore(members=[("a", a), ("b", b)], default="b")
    assert composite.load_index() is None


def test_invalidate_fans_out(two_paths):
    # Verify behaviorally: after invalidation, each member must observe a
    # fresh on-disk index rather than a stale cached one. We seed each
    # store, prime its cache via load_index(), then overwrite the on-disk
    # index out-of-band with a new entry. Without invalidation a stale
    # cache hides the new entry; with composite.invalidate_index_cache()
    # the next load surfaces it.
    pa, pb = two_paths
    a = SqliteToolSourceStore(url=_sqlite_url(pa))
    b = SqliteToolSourceStore(url=_sqlite_url(pb))
    a.store_index(ToolIndex(entries={"x": ToolIndexEntry(id="x")}))
    b.store_index(ToolIndex(entries={"y": ToolIndexEntry(id="y")}))
    a.load_index()
    b.load_index()

    # Out-of-band update via a fresh handle so the existing instance's
    # cache stays primed with the old value.
    SqliteToolSourceStore(url=_sqlite_url(pa)).store_index(
        ToolIndex(entries={"x": ToolIndexEntry(id="x"), "x2": ToolIndexEntry(id="x2")})
    )
    SqliteToolSourceStore(url=_sqlite_url(pb)).store_index(
        ToolIndex(entries={"y": ToolIndexEntry(id="y"), "y2": ToolIndexEntry(id="y2")})
    )

    # Pre-invalidation: stale caches still answer with the old contents.
    a_idx = a.load_index()
    b_idx = b.load_index()
    assert a_idx is not None
    assert b_idx is not None
    assert "x2" not in a_idx.entries
    assert "y2" not in b_idx.entries

    composite = CompositeToolSourceStore(members=[("a", a), ("b", b)], default="b")
    composite.invalidate_index_cache()

    # Post-invalidation: each member re-reads from disk and the new
    # entries surface through the merged index.
    merged = composite.load_index()
    assert merged is not None
    assert "x2" in merged.entries
    assert "y2" in merged.entries


def test_load_index_merges_entries_by_version(two_paths):
    pa, pb = two_paths
    a = SqliteToolSourceStore(url=_sqlite_url(pa))
    b = SqliteToolSourceStore(url=_sqlite_url(pb))
    idx_a = ToolIndex()
    idx_a.add_entry(ToolIndexEntry(id="multi", name="v1", version="1.0"))
    idx_a.add_entry(ToolIndexEntry(id="multi", name="v2", version="2.0"))
    a.store_index(idx_a)
    idx_b = ToolIndex()
    idx_b.add_entry(ToolIndexEntry(id="multi", name="v3", version="3.0"))
    b.store_index(idx_b)
    composite = CompositeToolSourceStore(members=[("a", a), ("b", b)], default="b")
    merged = composite.load_index()
    assert merged is not None
    for version, name in (("1.0", "v1"), ("2.0", "v2"), ("3.0", "v3")):
        entry = merged.get("multi", version)
        assert entry is not None
        assert entry.name == name


def test_list_source_paths_unions_members(two_paths):
    pa, pb = two_paths
    a = SqliteToolSourceStore(url=_sqlite_url(pa))
    b = SqliteToolSourceStore(url=_sqlite_url(pb))
    src_a = _src("ha", tool_id="ta")
    src_a.source_path = "/tools/a.xml"
    a.store(src_a)
    src_b = _src("hb", tool_id="tb")
    src_b.source_path = "/tools/b.xml"
    b.store(src_b)
    composite = CompositeToolSourceStore(members=[("a", a), ("b", b)], default="b")
    assert composite.list_source_paths() == {"/tools/a.xml", "/tools/b.xml"}


def test_read_only_member_names(two_paths):
    pa, pb = two_paths
    writable = SqliteToolSourceStore(url=_sqlite_url(pa))
    SqliteToolSourceStore(url=_sqlite_url(pb)).store(_src("h"))
    read_only = SqliteToolSourceStore(url=_sqlite_url(pb), read_only=True)
    composite = CompositeToolSourceStore(members=[("ro", read_only), ("rw", writable)], default="rw")
    assert composite.read_only_member_names == {"ro"}


def test_unavailable_read_only_member_disables_index_only_panel_initialization(two_paths):
    writable_path, _unused = two_paths
    writable = SqliteToolSourceStore(url=_sqlite_url(writable_path))
    unavailable = UnavailableToolSourceStore("no compatible cohort")
    composite = CompositeToolSourceStore(members=[("cvmfs", unavailable), ("rw", writable)], default="rw")
    box = CachedToolBox.__new__(CachedToolBox)
    box._store = composite
    box._tool_index = ToolIndex(entries={"local": ToolIndexEntry(id="local")})

    assert composite.unavailable_read_only_member_names == {"cvmfs"}
    assert box._init_tools_from_index([]) is False
