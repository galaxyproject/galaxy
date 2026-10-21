import os
import time

import pytest

from galaxy.util import watcher
from galaxy.util.bunch import Bunch

pytestmark = pytest.mark.skipif(not watcher.can_watch, reason="watchdog not available")


def get_watcher():
    return watcher.get_watcher(Bunch(watch_test="true"), "watch_test")


def watched_paths(observer):
    return {emitter.watch.path for emitter in observer.emitters}


def test_watchers_share_observer_and_watches(tmp_path):
    dir_a = os.path.realpath(tmp_path / "a")
    dir_b = os.path.realpath(tmp_path / "b")
    os.makedirs(dir_a)
    os.makedirs(dir_b)
    # One watcher per file, as TPV does
    watcher_a = get_watcher()
    watcher_b = get_watcher()
    watcher_c = get_watcher()
    for w, path in ((watcher_a, dir_a), (watcher_b, dir_b), (watcher_c, dir_b)):
        w.start()
        w.watch_file(os.path.join(path, "job_conf.yml"))
    observer = watcher_a.observer
    try:
        assert watcher_b.observer is observer
        assert watcher_c.observer is observer
        assert watched_paths(observer) == {dir_a, dir_b}

        watcher_a.shutdown()
        assert watched_paths(observer) == {dir_b}
        # still used by watcher_c
        watcher_b.shutdown()
        assert watched_paths(observer) == {dir_b}
        assert observer.is_alive()
    finally:
        for w in (watcher_a, watcher_b, watcher_c):
            w.shutdown()
    assert not observer.is_alive()


def test_callbacks_for_files_in_same_directory(tmp_path):
    path_a = os.path.realpath(tmp_path / "a.yml")
    path_b = os.path.realpath(tmp_path / "b.yml")
    called = []

    def failing_callback(path):
        raise Exception("callback failed")

    w = get_watcher()
    w.start()
    try:
        w.watch_file(path_a, callback=failing_callback)
        w.watch_file(path_b, callback=lambda path: called.append(path))
        # A failing callback must not stop the shared observer from handling later events
        with open(path_a, "w") as f:
            f.write("a")
        with open(path_b, "w") as f:
            f.write("b")
        deadline = time.time() + 10
        while path_b not in called and time.time() < deadline:
            time.sleep(0.1)
        assert path_b in called
    finally:
        w.shutdown()
