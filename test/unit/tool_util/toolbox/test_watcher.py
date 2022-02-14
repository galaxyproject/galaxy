import tempfile
import time
from contextlib import contextmanager
from os import path
from shutil import rmtree

import pytest

from galaxy.tool_util.toolbox import watcher
from galaxy.util import bunch


@pytest.mark.skipif(not watcher.can_watch, reason="watchdog not available")
def test_watcher():
    with __test_directory() as t:
        tool_path = path.join(t, "test.xml")
        toolbox = Toolbox()
        with open(tool_path, "w") as f:
            f.write("a")
        tool_watcher = watcher.get_tool_watcher(toolbox, bunch.Bunch(watch_tools=True))
        tool_watcher.start()
        tool_watcher.watch_file(tool_path, "cool_tool")
        time.sleep(2)
        assert not toolbox.was_reloaded("cool_tool")
        with open(tool_path, "w") as f:
            f.write("b")
        wait_for_reload(lambda: toolbox.was_reloaded("cool_tool"))
        tool_watcher.shutdown()
        assert tool_watcher.observer is None


@pytest.mark.skipif(not watcher.can_watch, reason="watchdog not available")
def test_tool_conf_watcher():
    callback = CallbackRecorder()
    conf_watcher = watcher.get_tool_conf_watcher(callback.call)
    conf_watcher.start()

    with __test_directory() as t:
        tool_conf_path = path.join(t, "test_conf.xml")
        with open(tool_conf_path, "w") as f:
            f.write("a")
        conf_watcher.watch_file(tool_conf_path)
        time.sleep(2)
        with open(tool_conf_path, "w") as f:
            f.write("b")
        wait_for_reload(lambda: callback.called)
        conf_watcher.shutdown()
        assert conf_watcher.thread is None


def wait_for_reload(check):
    reloaded = False
    for _ in range(10):
        reloaded = check()
        if reloaded:
            break
        time.sleep(0.2)
    assert reloaded


class Toolbox:
    def __init__(self):
        self.reloaded = {}

    def reload_tool_by_id(self, tool_id):
        self.reloaded[tool_id] = True

    def was_reloaded(self, tool_id):
        return self.reloaded.get(tool_id, False)


class CallbackRecorder:
    def __init__(self):
        self.called = False

    def call(self):
        self.called = True


@contextmanager
def __test_directory():
    base_path = tempfile.mkdtemp()
    try:
        yield base_path
    finally:
        rmtree(base_path)
