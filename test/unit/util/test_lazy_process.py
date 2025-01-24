"""Unit module for LazyProcess object in galaxy.util.lazy_process."""

import os
import tempfile
import time

from galaxy.util.lazy_process import LazyProcess


def test_lazy_process():
    """Create process, ensure start_process starts it and shutdown kills it."""
    t = tempfile.NamedTemporaryFile()
    os.remove(t.name)
    lazy_process = LazyProcess(["bash", "-c", f"touch {t.name}; sleep 100"])
    assert not os.path.exists(t.name)
    lazy_process.start_process()
    while not os.path.exists(t.name):
        time.sleep(0.01)
    assert lazy_process.process
    assert lazy_process.process.poll() is None
    lazy_process.shutdown()
    ret_val = None
    for _ in range(10):
        ret_val = lazy_process.process.poll()
        if ret_val is not None:
            break
        time.sleep(0.01)
    assert ret_val is not None
