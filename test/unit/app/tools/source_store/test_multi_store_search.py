from types import SimpleNamespace
from typing import (
    Any,
    cast,
)

import pytest

from galaxy.tools.cached_toolbox import CachedToolBox
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


class _FakeToolbox(CachedToolBox):
    def __init__(self, entries, views):
        self._tool_index = ToolIndex()
        for entry in entries:
            self._tool_index.add_entry(entry)
        self._views = views

    def panel_views(self):
        return [SimpleNamespace(id=view_id) for view_id in self._views]

    def panel_view_tool_ids(self, panel_view_id):
        return self._views[panel_view_id]


def _search(index_root, entries, views, search_config):
    config = search_config(_TUNING, index_root)
    toolbox = _FakeToolbox(entries, views)
    search = CachedToolboxSearch(config, toolbox)
    search.build_index(tool_cache=cast(Any, None), toolbox=toolbox)
    return search, config


def test_search_indexes_merged_runtime_tool_index(tmp_path, search_config):
    search, config = _search(
        str(tmp_path),
        [
            ToolIndexEntry(id="local_mapper", name="Sequence mapper", version="1.0"),
            ToolIndexEntry(id="cvmfs_mapper", name="Sequence mapper deluxe", version="2.0"),
        ],
        {"default": {"local_mapper", "cvmfs_mapper"}},
        search_config,
    )

    assert set(search.search("mapper", panel_view="default", config=config)) == {
        "local_mapper",
        "cvmfs_mapper",
    }


def test_search_without_index_dir_returns_empty(search_config):
    search, config = _search(
        None,
        [ToolIndexEntry(id="local_mapper", name="Sequence mapper", version="1.0")],
        {"default": {"local_mapper"}},
        search_config,
    )

    assert search.search("mapper", panel_view="default", config=config) == []


def test_search_unknown_panel_view_raises_key_error(tmp_path, search_config):
    search, config = _search(
        str(tmp_path),
        [ToolIndexEntry(id="local_mapper", name="Sequence mapper", version="1.0")],
        {"default": {"local_mapper"}},
        search_config,
    )

    with pytest.raises(KeyError):
        search.search("mapper", panel_view="does_not_exist", config=config)


def test_search_builds_distinct_panel_view_corpora(tmp_path, search_config):
    search, config = _search(
        str(tmp_path),
        [
            ToolIndexEntry(id="local_mapper", name="Sequence mapper", version="1.0"),
            ToolIndexEntry(id="other_mapper", name="Sequence mapper deluxe", version="1.0"),
        ],
        {"default": {"local_mapper", "other_mapper"}, "restricted": {"local_mapper"}},
        search_config,
    )

    assert set(search.search("mapper", panel_view="default", config=config)) == {
        "local_mapper",
        "other_mapper",
    }
    assert search.search("mapper", panel_view="restricted", config=config) == ["local_mapper"]
