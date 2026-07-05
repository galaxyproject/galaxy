"""Shared fixtures for tool source store unit tests."""

import pytest

from galaxy.tools.source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)


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
