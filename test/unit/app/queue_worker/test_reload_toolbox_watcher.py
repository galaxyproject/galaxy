import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

from galaxy import queue_worker
from galaxy.queue_worker import _get_new_toolbox
from galaxy.tools.lazy_toolbox import LazyToolBox


class FakeWatcher:
    def __init__(self):
        self.stopped = False

    def shutdown(self):
        self.stopped = True


def _fake_new_toolbox(*args, **kwargs):
    box = SimpleNamespace(data_manager_tools={})
    box.register_tool = lambda tool: None
    return box


def _fake_app(old_toolbox):
    app = SimpleNamespace()
    app._toolbox_lock = threading.RLock()
    app._toolbox = old_toolbox
    app.toolbox = old_toolbox
    app.datatypes_registry = MagicMock()
    app.tool_source_store = None
    app.config = SimpleNamespace(
        use_lazy_toolbox=False,
        tool_configs=[],
        tool_path="/tmp/tools",
        lazy_toolbox_cache_size=500,
    )
    return app


def _patch_builders(monkeypatch):
    monkeypatch.setattr(queue_worker, "ToolBox", _fake_new_toolbox)
    monkeypatch.setattr(queue_worker, "load_lib_tools", lambda toolbox: None)


def test_replacement_stops_superseded_lazy_watcher(monkeypatch):
    _patch_builders(monkeypatch)
    old = LazyToolBox.__new__(LazyToolBox)
    old.data_manager_tools = {}
    watcher = FakeWatcher()
    old._store_watcher = watcher  # type: ignore[assignment]
    app = _fake_app(old)

    _get_new_toolbox(app)

    assert watcher.stopped is True
    assert old._store_watcher is None
    assert app._toolbox is not old


def test_eager_old_toolbox_is_left_untouched(monkeypatch):
    _patch_builders(monkeypatch)
    old = SimpleNamespace(data_manager_tools={})
    app = _fake_app(old)

    _get_new_toolbox(app)

    assert app._toolbox is not old
    assert not hasattr(old, "_store_watcher")
