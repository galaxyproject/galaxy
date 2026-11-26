"""Unit module for LazyProcess object in galaxy.util.lazy_process."""

import os
import signal
import subprocess
import sys
import tempfile
import time

from galaxy.util.lazy_process import LazyProcess

SLOW_SIGTERM_EXIT = """
import signal, sys, time
def handler(signum, frame):
    time.sleep(0.2)
    sys.exit(0)
signal.signal(signal.SIGTERM, handler)
open(sys.argv[1], "w").close()
while True:
    time.sleep(0.01)
"""

IGNORE_SIGTERM = """
import signal, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
open(sys.argv[1], "w").close()
while True:
    time.sleep(0.01)
"""


def _started_lazy_process(command_and_args, ready_path):
    lazy_process = LazyProcess(command_and_args)
    lazy_process.start_process()
    while not os.path.exists(ready_path):
        time.sleep(0.01)
    assert lazy_process.process
    assert lazy_process.process.poll() is None
    return lazy_process


def _ready_path():
    t = tempfile.NamedTemporaryFile()
    os.remove(t.name)
    return t.name


def test_lazy_process():
    """Create process, ensure start_process starts it and shutdown kills it."""
    ready_path = _ready_path()
    lazy_process = _started_lazy_process(["bash", "-c", f"touch {ready_path}; sleep 100"], ready_path)
    assert lazy_process.running
    lazy_process.shutdown()
    assert lazy_process.process.poll() is not None
    assert not lazy_process.running


def test_shutdown_waits_for_graceful_exit():
    ready_path = _ready_path()
    lazy_process = _started_lazy_process([sys.executable, "-c", SLOW_SIGTERM_EXIT, ready_path], ready_path)
    lazy_process.shutdown()
    assert lazy_process.process.returncode == 0


def test_shutdown_kills_process_ignoring_sigterm():
    ready_path = _ready_path()
    lazy_process = _started_lazy_process([sys.executable, "-c", IGNORE_SIGTERM, ready_path], ready_path)
    lazy_process.shutdown(timeout=0.5)
    assert lazy_process.process.returncode == -signal.SIGKILL


def test_running_false_after_clean_exit():
    lazy_process = LazyProcess(["true"])
    lazy_process.process = subprocess.Popen(["true"])
    lazy_process.process.wait()
    assert not lazy_process.running
