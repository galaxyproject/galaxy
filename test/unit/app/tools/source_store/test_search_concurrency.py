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
from typing import cast

from galaxy.config import GalaxyAppConfiguration
from galaxy.tools.search import CachedToolboxSearch
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
