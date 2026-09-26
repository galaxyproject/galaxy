import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock
from unittest.mock import Mock

import pytest

from galaxy.tools import cache as cache_module
from galaxy.tools.cache import ToolCache
from galaxy.util.hash_util import md5_hash_file


def test_hash_initialization_is_lazy(tmp_path):
    path = tmp_path / "tool.xml"
    path.write_text("original")
    cache = ToolCache()
    cache.cache_tool(path, Mock(id="tool", _macro_paths=[]))
    assert cache._hash_by_tool_paths[str(path)]._tool_hash is None

    cache.assert_hashes_initialized()

    assert cache._hash_by_tool_paths[str(path)]._tool_hash is not None
    assert cache._hashes_initialized


@pytest.mark.parametrize("changed_file", ["tool.xml", "macros.xml"])
def test_cache_tool_during_hash_initialization(tmp_path, monkeypatch, changed_file):
    cache = ToolCache()
    initial = tmp_path / "initial.xml"
    config = tmp_path / "tool.xml"
    macro = tmp_path / "macros.xml"
    for path in (initial, config, macro):
        path.write_text("original")
    cache.cache_tool(initial, Mock(id="initial", all_ids=["initial"], _macro_paths=[]))

    hashing_started = Event()
    insertion_waiting = Event()
    finish_hashing = Event()

    class ObservedLock:
        """Expose the insertion's lock attempt without relying on thread timing."""

        def __init__(self):
            self.lock = Lock()

        def __enter__(self):
            if hashing_started.is_set():
                insertion_waiting.set()
            self.lock.acquire()

        def __exit__(self, *args):
            self.lock.release()

    observed_lock = ObservedLock()
    monkeypatch.setattr(cache, "_lock", observed_lock)

    def blocking_hash(path):
        # Iteration and publication of initialization must share the writer's lock.
        assert observed_lock.lock.locked()
        if path == initial:
            hashing_started.set()
            assert finish_hashing.wait(5)
        return md5_hash_file(path)

    monkeypatch.setattr(cache_module, "md5_hash_file", blocking_hash)
    tool = Mock(id="tool", all_ids=["tool"], _macro_paths=[macro])
    with ThreadPoolExecutor(max_workers=2) as executor:
        initialization = executor.submit(cache.assert_hashes_initialized)
        try:
            assert hashing_started.wait(5)
            insertion = executor.submit(cache.cache_tool, config, tool)
            assert insertion_waiting.wait(5)
            assert cache.get_tool(config) is None
        finally:
            finish_hashing.set()
        initialization.result(timeout=5)
        insertion.result(timeout=5)

    assert cache._hashes_initialized
    for path in (initial, config, macro):
        assert cache._hash_by_tool_paths[str(path)]._tool_hash == md5_hash_file(path)

    # A tool added while initialization runs must have a baseline for later edits.
    changed_path = tmp_path / changed_file
    old_mtime = changed_path.stat().st_mtime
    changed_path.write_text("edited")
    os.utime(changed_path, (old_mtime + 10, old_mtime + 10))
    assert cache.cleanup() == ["tool"]
    assert cache.get_tool(config) is None
    assert cache.get_tool(initial) is not None
