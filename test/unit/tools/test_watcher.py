import tempfile
import time

from contextlib import contextmanager
from os import path
from shutil import rmtree

from galaxy.tools.toolbox import watcher
from galaxy.util import bunch


def test_watcher():
    if not watcher.can_watch:
        from nose.plugins.skip import SkipTest
        raise SkipTest()

    with __test_directory() as t:
        tool_path = path.join(t, "test.xml")
        toolbox = Toolbox()
        open(tool_path, "w").write("a")
        tool_watcher = watcher.get_tool_watcher(toolbox, bunch.Bunch(
            watch_tools=True
        ))
        time.sleep(1)
        tool_watcher.watch_file(tool_path, "cool_tool")
        assert not toolbox.was_reloaded("cool_tool")
        open(tool_path, "w").write("b")
        wait_for_reload(lambda: toolbox.was_reloaded("cool_tool"))
        tool_watcher.shutdown()
        assert not tool_watcher.observer.is_alive()


def test_tool_conf_watcher():
    if not watcher.can_watch:
        from nose.plugins.skip import SkipTest
        raise SkipTest()

    callback = CallbackRecorder()
    conf_watcher = watcher.get_tool_conf_watcher(callback.call)

    with __test_directory() as t:
        tool_conf_path = path.join(t, "test_conf.xml")
        conf_watcher.watch_file(tool_conf_path)
        time.sleep(1)
        open(tool_conf_path, "w").write("b")
        wait_for_reload(lambda: callback.called)
        conf_watcher.shutdown()
        assert not conf_watcher.thread.is_alive()


def wait_for_reload(check):
    reloaded = False
    for i in range(10):
        reloaded = check()
        if reloaded:
            break
        time.sleep(.2)
    assert reloaded


class Toolbox(object):

    def __init__(self):
        self.reloaded = {}

    def reload_tool_by_id( self, tool_id ):
        self.reloaded[ tool_id ] = True

    def was_reloaded(self, tool_id):
        return self.reloaded.get( tool_id, False )


class CallbackRecorder(object):

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
