"""Check that the unit tests' pytest configuration doesn't keep test state alive.

Each test runs a small pytest session in a subprocess with copies of the unit
tests' ``conftest.py`` and the root ``pytest.ini``.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

GALAXY_ROOT = Path(__file__).parents[2]

CLASS_STATE_MODULE = """
import gc
import weakref

STATE_REFS = []


class State:
    pass


class TestStoresStateOnSelf:
    def setup_method(self):
        self.state = State()
        STATE_REFS.append(weakref.ref(self.state))

    def test_first(self):
        assert self.state is not None

    def test_second(self):
        assert self.state is not None


def test_state_of_finished_class_tests_is_released():
    gc.collect()
    assert len(STATE_REFS) == 2
    assert [ref() for ref in STATE_REFS] == [None, None]
"""

UNCLOSED_SQLITE_MODULE = """
import gc
import sqlite3


def live_connections():
    return [o for o in gc.get_objects() if isinstance(o, sqlite3.Connection)]


def test_leaves_connection_unclosed():
    sqlite3.connect(":memory:")
    gc.collect()


def test_unclosed_connection_is_released():
    gc.collect()
    assert live_connections() == []
"""


def run_pytest(tmp_path, test_module, *python_args):
    shutil.copy(GALAXY_ROOT / "test" / "unit" / "conftest.py", tmp_path / "conftest.py")
    shutil.copy(GALAXY_ROOT / "pytest.ini", tmp_path / "pytest.ini")
    (tmp_path / "test_module.py").write_text(test_module)
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_ADDOPTS"}
    result = subprocess.run(
        [
            sys.executable,
            *python_args,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "-p",
            "no:xdist",
            "-p",
            "no:cov",
            "test_module.py",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_test_class_instance_state_is_released_after_teardown(tmp_path):
    run_pytest(tmp_path, CLASS_STATE_MODULE)


@pytest.mark.skipif(sys.version_info < (3, 13), reason="sqlite3 warns about unclosed connections since Python 3.13")
def test_unclosed_sqlite_connection_warning_does_not_keep_connection_alive(tmp_path):
    # pytest-cov un-ignores this ResourceWarning for the whole session, as -W does here.
    run_pytest(tmp_path, UNCLOSED_SQLITE_MODULE, "-W", "default::ResourceWarning")
