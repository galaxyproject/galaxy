from types import SimpleNamespace
from typing import cast

import pytest

from galaxy.config import GalaxyAppConfiguration
from galaxy.tools.search import CachedToolboxSearch
from galaxy.tools.source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tools.source_store.search import ToolSearchTuning

_TUNING = ToolSearchTuning(
    id_boost=9.0,
    name_boost=9.0,
    name_exact_multiplier=10.0,
    stub_boost=2.0,
    section_boost=1.0,
    description_boost=0.5,
    label_boost=1.0,
    ngram_minsize=3,
    ngram_maxsize=4,
    enable_ngram_search=False,
    ngram_factor=0.2,
)


class _FakeToolbox:
    def __init__(self, entries, views):
        self.tool_index = ToolIndex()
        for entry in entries:
            self.tool_index.add_entry(entry)
        self._views = views

    def panel_views(self):
        return [SimpleNamespace(id=view_id) for view_id in self._views]

    def panel_view_tool_ids(self, panel_view_id):
        return self._views[panel_view_id]


def _config(index_root):
    return cast(
        GalaxyAppConfiguration,
        SimpleNamespace(tool_search_index_dir=index_root),
    )


def _search(index_root, entries, views, monkeypatch):
    monkeypatch.setattr(ToolSearchTuning, "from_config", classmethod(lambda cls, config: _TUNING))
    config = _config(index_root)
    toolbox = _FakeToolbox(entries, views)
    search = CachedToolboxSearch(config, toolbox)  # type: ignore[arg-type]
    search.build_index(tool_cache=None, toolbox=toolbox)
    return search, config


def test_search_indexes_merged_runtime_tool_index(tmp_path, monkeypatch):
    search, config = _search(
        str(tmp_path),
        [
            ToolIndexEntry(id="local_mapper", name="Sequence mapper", version="1.0"),
            ToolIndexEntry(id="cvmfs_mapper", name="Sequence mapper deluxe", version="2.0"),
        ],
        {"default": {"local_mapper", "cvmfs_mapper"}},
        monkeypatch,
    )

    assert set(search.search("mapper", panel_view="default", config=config)) == {
        "local_mapper",
        "cvmfs_mapper",
    }


def test_search_without_index_dir_returns_empty(monkeypatch):
    search, config = _search(
        None,
        [ToolIndexEntry(id="local_mapper", name="Sequence mapper", version="1.0")],
        {"default": {"local_mapper"}},
        monkeypatch,
    )

    assert search.search("mapper", panel_view="default", config=config) == []


def test_search_unknown_panel_view_raises_key_error(tmp_path, monkeypatch):
    search, config = _search(
        str(tmp_path),
        [ToolIndexEntry(id="local_mapper", name="Sequence mapper", version="1.0")],
        {"default": {"local_mapper"}},
        monkeypatch,
    )

    with pytest.raises(KeyError):
        search.search("mapper", panel_view="does_not_exist", config=config)


def test_search_builds_distinct_panel_view_corpora(tmp_path, monkeypatch):
    search, config = _search(
        str(tmp_path),
        [
            ToolIndexEntry(id="local_mapper", name="Sequence mapper", version="1.0"),
            ToolIndexEntry(id="other_mapper", name="Sequence mapper deluxe", version="1.0"),
        ],
        {"default": {"local_mapper", "other_mapper"}, "restricted": {"local_mapper"}},
        monkeypatch,
    )

    assert set(search.search("mapper", panel_view="default", config=config)) == {
        "local_mapper",
        "other_mapper",
    }
    assert search.search("mapper", panel_view="restricted", config=config) == ["local_mapper"]
