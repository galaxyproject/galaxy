"""Shared fixtures for tool source store unit tests."""

from types import SimpleNamespace
from typing import cast

import pytest

from galaxy.config import GalaxyAppConfiguration
from galaxy.tools.source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tools.source_store.search import ToolSearchTuning


@pytest.fixture
def index_entry():
    def _make(id, version=None, **kwargs):
        return ToolIndexEntry(id=id, version=version, **kwargs)

    return _make


@pytest.fixture
def tool_index(index_entry):
    def _make(*entries):
        index = ToolIndex()
        for entry in entries:
            index.add_entry(entry)
        return index

    return _make


@pytest.fixture
def search_config():
    """Build a real tuning-compatible config without patching from_config."""

    def _make(tuning: ToolSearchTuning, index_dir: str | None = None) -> GalaxyAppConfiguration:
        return cast(
            GalaxyAppConfiguration,
            SimpleNamespace(
                tool_id_boost=tuning.id_boost,
                tool_name_boost=tuning.name_boost,
                tool_name_exact_multiplier=tuning.name_exact_multiplier,
                tool_stub_boost=tuning.stub_boost,
                tool_section_boost=tuning.section_boost,
                tool_description_boost=tuning.description_boost,
                tool_label_boost=tuning.label_boost,
                tool_ngram_minsize=tuning.ngram_minsize,
                tool_ngram_maxsize=tuning.ngram_maxsize,
                tool_enable_ngram_search=tuning.enable_ngram_search,
                tool_ngram_factor=tuning.ngram_factor,
                tool_help_boost=tuning.help_boost,
                index_tool_help=tuning.index_tool_help,
                tool_help_bm25f_k1=tuning.help_bm25f_k1,
                tool_search_index_dir=index_dir,
            ),
        )

    return _make
