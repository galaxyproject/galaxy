from types import SimpleNamespace
from typing import cast

import pytest

from galaxy.config import GalaxyAppConfiguration
from galaxy.tools.search import LazyToolboxSearch
from galaxy.tools.source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tools.source_store.populator import (
    DEFAULT_STORE_NAME,
    whoosh_dir_for_store,
)
from galaxy.tools.source_store.search import (
    ToolSearchTuning,
    ToolWhooshIndex,
)

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


def _build_store_index(index_root, store_name, entries):
    tool_index = ToolIndex()
    for entry in entries:
        tool_index.add_entry(entry)
    index_dir = whoosh_dir_for_store(index_root, store_name)
    assert index_dir
    whoosh = ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING)
    assert whoosh.build(tool_index) == len(entries)


def test_search_merges_hits_across_store_indexes(tmp_path, monkeypatch):
    monkeypatch.setattr(ToolSearchTuning, "from_config", classmethod(lambda cls, config: _TUNING))
    index_root = str(tmp_path)
    _build_store_index(
        index_root,
        DEFAULT_STORE_NAME,
        [ToolIndexEntry(id="local_mapper", name="Sequence mapper", version="1.0")],
    )
    _build_store_index(
        index_root,
        "cvmfs_main",
        [ToolIndexEntry(id="cvmfs_mapper", name="Sequence mapper deluxe", version="2.0")],
    )
    config = cast(
        GalaxyAppConfiguration,
        SimpleNamespace(
            tool_search_index_dir=index_root,
            tool_source_stores={"cvmfs_main": {"type": "sqlalchemy"}},
        ),
    )
    hits = LazyToolboxSearch(config).search("mapper", panel_view="default", config=config)
    assert set(hits) == {"local_mapper", "cvmfs_mapper"}


def test_search_without_index_dir_returns_empty():
    config = cast(GalaxyAppConfiguration, SimpleNamespace(tool_search_index_dir=None, tool_source_stores={}))
    assert LazyToolboxSearch(config).search("mapper", panel_view="default", config=config) == []


class _FakeToolbox:
    def __init__(self, views):
        self._views = views

    def panel_view_tool_ids(self, panel_view_id):
        return self._views[panel_view_id]


def _single_store_config(index_root):
    return cast(
        GalaxyAppConfiguration,
        SimpleNamespace(tool_search_index_dir=index_root, tool_source_stores={}),
    )


def test_search_unknown_panel_view_raises_key_error(tmp_path, monkeypatch):
    monkeypatch.setattr(ToolSearchTuning, "from_config", classmethod(lambda cls, config: _TUNING))
    index_root = str(tmp_path)
    _build_store_index(
        index_root, DEFAULT_STORE_NAME, [ToolIndexEntry(id="local_mapper", name="Sequence mapper", version="1.0")]
    )
    config = _single_store_config(index_root)
    search = LazyToolboxSearch(config, _FakeToolbox({"default": {"local_mapper"}}))  # type: ignore[arg-type]
    with pytest.raises(KeyError):
        search.search("mapper", panel_view="does_not_exist", config=config)


def test_search_scopes_hits_to_requested_panel_view(tmp_path, monkeypatch):
    monkeypatch.setattr(ToolSearchTuning, "from_config", classmethod(lambda cls, config: _TUNING))
    index_root = str(tmp_path)
    _build_store_index(
        index_root,
        DEFAULT_STORE_NAME,
        [
            ToolIndexEntry(id="local_mapper", name="Sequence mapper", version="1.0"),
            ToolIndexEntry(id="other_mapper", name="Sequence mapper deluxe", version="1.0"),
        ],
    )
    config = _single_store_config(index_root)
    search = LazyToolboxSearch(
        config,
        _FakeToolbox({"default": {"local_mapper", "other_mapper"}, "restricted": {"local_mapper"}}),  # type: ignore[arg-type]
    )
    assert set(search.search("mapper", panel_view="default", config=config)) == {"local_mapper", "other_mapper"}
    # The restricted view holds only one of the two matching tools; the
    # out-of-view hit must be dropped.
    assert search.search("mapper", panel_view="restricted", config=config) == ["local_mapper"]
