from datetime import (
    datetime,
    timedelta,
    timezone,
)
from types import SimpleNamespace
from unittest.mock import MagicMock

from galaxy import tools
from galaxy.tools import ToolBox
from galaxy.tools.source_store.interface import StoredToolSource


def _stored(tool_id=None, source_path=None, raw="<tool/>", stored_at=None):
    return StoredToolSource(
        hash=f"{tool_id}:{source_path}:{raw}",
        tool_source_class="XmlToolSource",
        raw_source=raw,
        tool_id=tool_id,
        source_path=source_path,
        stored_at=stored_at,
    )


def _box(store):
    box = ToolBox.__new__(ToolBox)
    box.app = SimpleNamespace(config=SimpleNamespace(use_lazy_toolbox=True), tool_source_store=store)  # type: ignore[assignment]
    return box


def _patch_get_tool_source(monkeypatch):
    monkeypatch.setattr(tools, "get_tool_source", lambda raw_tool_source, tool_source_class: raw_tool_source)


def test_path_row_preferred_over_tool_id_rows(monkeypatch):
    _patch_get_tool_source(monkeypatch)
    store = MagicMock()
    store.get_by_source_path.return_value = _stored(tool_id="t1", source_path="/tools/t1.xml", raw="path_row")
    store.get_by_tool_id.return_value = [_stored(tool_id="t1", raw="guid_row")]
    box = _box(store)

    assert box._get_tool_source_from_store("/tools/t1.xml", tool_id="t1") == "path_row"
    store.get_by_tool_id.assert_not_called()


def test_tool_id_fallback_when_path_misses(monkeypatch):
    _patch_get_tool_source(monkeypatch)
    store = MagicMock()
    store.get_by_source_path.return_value = None
    store.get_by_tool_id.return_value = [_stored(tool_id="t1", raw="guid_row")]
    box = _box(store)

    assert box._get_tool_source_from_store("/tools/t1.xml", tool_id="t1") == "guid_row"


def test_tool_id_fallback_picks_latest_stored_at(monkeypatch):
    _patch_get_tool_source(monkeypatch)
    now = datetime.now(timezone.utc)
    store = MagicMock()
    store.get_by_source_path.return_value = None
    store.get_by_tool_id.return_value = [
        _stored(tool_id="t1", raw="old", stored_at=now - timedelta(hours=1)),
        _stored(tool_id="t1", raw="new", stored_at=now),
        _stored(tool_id="t1", raw="mid", stored_at=now - timedelta(minutes=30)),
    ]
    box = _box(store)

    assert box._get_tool_source_from_store("/tools/t1.xml", tool_id="t1") == "new"


def test_tool_id_fallback_prefers_dated_row_over_undated(monkeypatch):
    _patch_get_tool_source(monkeypatch)
    now = datetime.now(timezone.utc)
    store = MagicMock()
    store.get_by_source_path.return_value = None
    store.get_by_tool_id.return_value = [
        _stored(tool_id="t1", raw="dated", stored_at=now),
        _stored(tool_id="t1", raw="undated", stored_at=None),
    ]
    box = _box(store)

    assert box._get_tool_source_from_store("/tools/t1.xml", tool_id="t1") == "dated"


def test_returns_none_when_lazy_toolbox_disabled():
    store = MagicMock()
    box = ToolBox.__new__(ToolBox)
    box.app = SimpleNamespace(config=SimpleNamespace(use_lazy_toolbox=False), tool_source_store=store)  # type: ignore[assignment]

    assert box._get_tool_source_from_store("/tools/t1.xml", tool_id="t1") is None
    store.get_by_source_path.assert_not_called()
    store.get_by_tool_id.assert_not_called()
