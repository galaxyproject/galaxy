from contextlib import contextmanager
from os import path
from shutil import rmtree
import tempfile
import time

from galaxy.tools import watcher
from galaxy.util import bunch


def test_watcher():
    if not watcher.can_watch:
        from nose.plugins.skip import SkipTest
        raise SkipTest()

    with __test_directory() as t:
        tool_path = path.join(t, "test.xml")
        toolbox = Toolbox()
        open(tool_path, "w").write("a")
        tool_watcher = watcher.get_watcher(toolbox, bunch.Bunch(
            watch_tools=True
        ))
        tool_watcher.watch_file(tool_path, "cool_tool")
        open(tool_path, "w").write("b")
        time.sleep(2)
        toolbox.assert_reloaded("cool_tool")


class Toolbox(object):

    def __init__(self):
        self.reloaded = {}

    def reload_tool_by_id( self, tool_id ):
        self.reloaded[ tool_id ] = True

    def assert_reloaded(self, tool_id):
        assert self.reloaded.get( tool_id, False )


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
