"""Concurrent ``CachedToolboxSearch.build_index`` calls must not corrupt the index.

``reindex_tool_search`` reaches ``build_index`` from several threads at once
(boot, the ``rebuild_toolbox_search_index`` control task, and
``remove_tool_by_id``). Without serialization two builds race on the same
on-disk Whoosh directories and one thread's ``create_in``/``rmtree`` pulls the
segment files out from under the other, surfacing as ``whoosh.index.LockError``
or a fatal ``FileNotFoundError`` on the segment TOC.
"""

import threading
from types import SimpleNamespace
from typing import (
    Any,
    cast,
    NamedTuple,
)

from whoosh import index as whoosh_index

from galaxy.config import GalaxyAppConfiguration
from galaxy.tools.search import (
    CachedToolboxSearch,
    INDEX_BUILD_MAX_RETRIES,
)
from galaxy.tools.source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tools.source_store.search import ToolSearchTuning

_TUNING = ToolSearchTuning(
    id_boost=20.0,
    name_boost=10.0,
    name_exact_multiplier=2.0,
    stub_boost=5.0,
    section_boost=4.0,
    description_boost=3.0,
    label_boost=3.0,
    ngram_minsize=3,
    ngram_maxsize=4,
    enable_ngram_search=True,
    ngram_factor=0.5,
)


class _FakeCachedToolbox:
    """Minimal ``SupportsCachedSearch`` surface over a static index."""

    def __init__(self, index: ToolIndex, panel_view_ids: list[str]) -> None:
        self._index = index
        self._panel_view_ids = panel_view_ids
        self._reload_count = 0

    @property
    def tool_index(self) -> ToolIndex:
        return self._index

    def panel_views(self):
        return [SimpleNamespace(id=view_id) for view_id in self._panel_view_ids]

    def panel_view_tool_ids(self, panel_view_id: str) -> set[str]:
        return set(self._index.entries)


def test_concurrent_build_index_does_not_corrupt(tmp_path, search_config):
    index = ToolIndex()
    for name in ("mapper", "caller", "trimmer", "aligner", "sorter"):
        index.add_entry(ToolIndexEntry(id=name, version="1.0", name=name.title()))
    # Several panel views multiply the on-disk dirs each build touches, widening
    # the window two racing builds can collide in.
    toolbox = _FakeCachedToolbox(index, ["default", "my_panel", "ontology:edam_operations"])
    config = search_config(_TUNING, index_dir=str(tmp_path / "tool_search_index"))
    search = CachedToolboxSearch(cast(GalaxyAppConfiguration, config), toolbox=toolbox)

    errors: list[Exception] = []
    start = threading.Barrier(8)

    def build_repeatedly() -> None:
        start.wait()
        try:
            for _ in range(6):
                search.build_index(tool_cache=None, toolbox=toolbox)  # type: ignore[arg-type]
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=build_repeatedly) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert all(not thread.is_alive() for thread in threads)
    assert not errors, f"Concurrent build_index raised: {errors!r}"
    # The index is intact and queryable after the concurrent hammering.
    assert search.search("mapper", "default", config) == ["mapper"]


def test_build_index_blocked_by_another_writer_stays_stale(tmp_path, search_config, monkeypatch):
    monkeypatch.setattr("galaxy.tools.source_store.search.INDEX_WRITE_LOCK_TIMEOUT", 0.1)
    index = ToolIndex()
    index.add_entry(ToolIndexEntry(id="mapper", version="1.0", name="Mapper"))
    toolbox = _FakeCachedToolbox(index, ["default"])
    config = search_config(_TUNING, index_dir=str(tmp_path / "tool_search_index"))
    search = CachedToolboxSearch(cast(GalaxyAppConfiguration, config), toolbox=toolbox)
    search.build_index(tool_cache=None, toolbox=toolbox)  # type: ignore[arg-type]
    index.add_entry(ToolIndexEntry(id="trimmer", version="1.0", name="Trimmer"))

    other_writer = whoosh_index.open_dir(search.cached_panel_searches["default"].index_dir).writer()
    try:
        search.build_index(tool_cache=None, toolbox=toolbox)  # type: ignore[arg-type]
    finally:
        other_writer.cancel()

    assert search.build_index_if_stale(tool_cache=None, toolbox=toolbox)  # type: ignore[arg-type]
    assert search.search("trimmer", "default", cast(GalaxyAppConfiguration, config)) == ["trimmer"]


class _BlockedBuild(NamedTuple):
    search: CachedToolboxSearch
    toolbox: _FakeCachedToolbox
    config: GalaxyAppConfiguration
    other_writer: Any
    retries: list[int]
    retries_exhausted: threading.Event


def _blocked_build(tmp_path, search_config, retry_delay: float) -> _BlockedBuild:
    """Build ``mapper``, add ``trimmer`` and build again while another writer holds the lock."""
    index = ToolIndex()
    index.add_entry(ToolIndexEntry(id="mapper", version="1.0", name="Mapper"))
    toolbox = _FakeCachedToolbox(index, ["default"])
    config = search_config(_TUNING, index_dir=str(tmp_path / "tool_search_index"))
    retries: list[int] = []
    retries_exhausted = threading.Event()

    def retry_build() -> None:
        retries.append(1)
        search.build_index_if_stale(tool_cache=None, toolbox=toolbox)  # type: ignore[arg-type]
        if len(retries) == INDEX_BUILD_MAX_RETRIES:
            retries_exhausted.set()

    search = CachedToolboxSearch(
        cast(GalaxyAppConfiguration, config), toolbox=toolbox, retry_build=retry_build, retry_delay=retry_delay
    )
    search.build_index(tool_cache=None, toolbox=toolbox)  # type: ignore[arg-type]
    index.add_entry(ToolIndexEntry(id="trimmer", version="1.0", name="Trimmer"))
    other_writer = whoosh_index.open_dir(search.cached_panel_searches["default"].index_dir).writer()
    try:
        search.build_index(tool_cache=None, toolbox=toolbox)  # type: ignore[arg-type]
    except BaseException:
        other_writer.cancel()
        raise
    return _BlockedBuild(search, toolbox, config, other_writer, retries, retries_exhausted)


def test_build_index_blocked_by_another_writer_retries_after_the_lock_is_released(tmp_path, search_config, monkeypatch):
    monkeypatch.setattr("galaxy.tools.source_store.search.INDEX_WRITE_LOCK_TIMEOUT", 0.1)
    blocked = _blocked_build(tmp_path, search_config, retry_delay=0.1)
    try:
        assert blocked.search.indexed_reload_count is None
        blocked.other_writer.cancel()
        assert blocked.search.wait_until_current(blocked.toolbox, timeout=10)  # type: ignore[arg-type]
        assert blocked.search.search("trimmer", "default", blocked.config) == ["trimmer"]
    finally:
        blocked.search.shutdown()


def test_build_index_retries_are_bounded(tmp_path, search_config, monkeypatch):
    monkeypatch.setattr("galaxy.tools.source_store.search.INDEX_WRITE_LOCK_TIMEOUT", 0.01)
    blocked = _blocked_build(tmp_path, search_config, retry_delay=0.01)
    try:
        assert blocked.retries_exhausted.wait(timeout=10)
        assert not blocked.search.wait_until_current(blocked.toolbox, timeout=1)  # type: ignore[arg-type]
        assert len(blocked.retries) == INDEX_BUILD_MAX_RETRIES
    finally:
        blocked.other_writer.cancel()
        blocked.search.shutdown()


def test_blocked_build_after_exhausted_retries_retries_again(tmp_path, search_config, monkeypatch):
    monkeypatch.setattr("galaxy.tools.source_store.search.INDEX_WRITE_LOCK_TIMEOUT", 0.01)
    blocked = _blocked_build(tmp_path, search_config, retry_delay=0.01)
    try:
        assert blocked.retries_exhausted.wait(timeout=10)
        blocked.search.build_index(tool_cache=None, toolbox=blocked.toolbox)  # type: ignore[arg-type]
    finally:
        blocked.other_writer.cancel()
    try:
        assert blocked.search.wait_until_current(blocked.toolbox, timeout=10)  # type: ignore[arg-type]
        assert len(blocked.retries) > INDEX_BUILD_MAX_RETRIES
    finally:
        blocked.search.shutdown()


def test_shutdown_cancels_a_pending_build_retry(tmp_path, search_config, monkeypatch):
    monkeypatch.setattr("galaxy.tools.source_store.search.INDEX_WRITE_LOCK_TIMEOUT", 0.1)
    blocked = _blocked_build(tmp_path, search_config, retry_delay=0.5)
    blocked.search.shutdown()
    blocked.other_writer.cancel()
    assert not blocked.search.wait_until_current(blocked.toolbox, timeout=2)  # type: ignore[arg-type]
    assert blocked.retries == []
