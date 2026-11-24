import os
import queue
import subprocess
import sys
import textwrap
import threading
from types import SimpleNamespace
from unittest import mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from galaxy.tool_shed.galaxy_install import (
    install_manager,
    installed_repository_manager,
)
from galaxy.tool_shed.galaxy_install.metadata.installed_repository_metadata_manager import (
    InstalledRepositoryMetadataManager,
)
from galaxy.tool_shed.galaxy_install.repository_operation_lock import repository_operation_lock
from galaxy.tool_shed.util import shed_util_common

ACQUIRE_IN_OTHER_PROCESS = textwrap.dedent("""
    import sys
    from types import SimpleNamespace

    from sqlalchemy import create_engine

    from galaxy.tool_shed.galaxy_install.repository_operation_lock import repository_operation_lock

    database_url, data_dir, mode = sys.argv[1:]
    app = SimpleNamespace(
        install_model=SimpleNamespace(engine=create_engine(database_url)), config=SimpleNamespace(data_dir=data_dir)
    )
    print("ready", flush=True)
    sys.stdin.readline()
    with repository_operation_lock(app):
        print("acquired", flush=True)
        if mode == "hold":
            sys.stdin.readline()
    """)

# Long enough for an unlocked acquire in another thread or process to finish, short enough to keep the suite fast.
BLOCKED_WAIT = 1.5


@pytest.fixture(params=["sqlite", "postgresql"])
def database_url(request):
    if request.param == "sqlite":
        return "sqlite://"
    url = os.environ.get("GALAXY_TEST_DBURI") or os.environ.get("GALAXY_TEST_CONNECT_POSTGRES_URI")
    if not url or make_url(url).get_backend_name() != "postgresql":
        pytest.skip("Set GALAXY_TEST_DBURI to a PostgreSQL URL to exercise the advisory lock")
    return url


def _lock_app(database_url, data_dir):
    return SimpleNamespace(
        install_model=SimpleNamespace(engine=create_engine(database_url)),
        config=SimpleNamespace(data_dir=str(data_dir)),
    )


class _OtherProcess:
    def __init__(self, database_url, data_dir, mode):
        self.process = subprocess.Popen(
            [sys.executable, "-c", ACQUIRE_IN_OTHER_PROCESS, database_url, str(data_dir), mode],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
        )
        self.lines: queue.Queue[str] = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()
        assert self.next_line(timeout=60) == "ready"

    def _read(self):
        assert self.process.stdout
        for line in self.process.stdout:
            self.lines.put(line.strip())

    def send(self):
        assert self.process.stdin
        self.process.stdin.write("\n")
        self.process.stdin.flush()

    def next_line(self, timeout):
        return self.lines.get(timeout=timeout)

    def stop(self):
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=30)


class _OtherThread:
    def __init__(self, app):
        self.acquired = threading.Event()
        self.thread = threading.Thread(target=self._acquire, args=(app,), daemon=True)
        self.thread.start()

    def _acquire(self, app):
        with repository_operation_lock(app):
            self.acquired.set()

    def join(self):
        self.thread.join(timeout=30)
        assert self.acquired.is_set()


def test_lock_excludes_other_processes(database_url, tmp_path):
    app = _lock_app(database_url, tmp_path)
    other = _OtherProcess(database_url, tmp_path, mode="release")
    try:
        with repository_operation_lock(app):
            other.send()
            with pytest.raises(queue.Empty):
                other.next_line(timeout=BLOCKED_WAIT)
        assert other.next_line(timeout=30) == "acquired"
    finally:
        other.stop()


def test_lock_is_released_when_holder_process_dies(database_url, tmp_path):
    app = _lock_app(database_url, tmp_path)
    holder = _OtherProcess(database_url, tmp_path, mode="hold")
    try:
        holder.send()
        assert holder.next_line(timeout=30) == "acquired"
        waiter = _OtherThread(app)
        assert not waiter.acquired.wait(timeout=BLOCKED_WAIT)
        holder.process.kill()
        waiter.join()
    finally:
        holder.stop()


def test_lock_excludes_other_threads(database_url, tmp_path):
    app = _lock_app(database_url, tmp_path)
    with repository_operation_lock(app):
        other = _OtherThread(app)
        assert not other.acquired.wait(timeout=BLOCKED_WAIT)
    other.join()


def test_lock_is_reentrant_within_a_thread(database_url, tmp_path):
    app = _lock_app(database_url, tmp_path)
    nested_done = threading.Event()

    def nested():
        with repository_operation_lock(app):
            with repository_operation_lock(app):
                pass
            # Still held after the inner block exits.
            other = _OtherThread(app)
            assert not other.acquired.wait(timeout=BLOCKED_WAIT)
        other.join()
        nested_done.set()

    thread = threading.Thread(target=nested, daemon=True)
    thread.start()
    thread.join(timeout=30)
    assert nested_done.is_set()


class _StopOperation(Exception):
    pass


def _probe_lock_then_stop(app, held):
    def probe(*args, **kwargs):
        other = _OtherThread(app)
        held.append(not other.acquired.wait(timeout=BLOCKED_WAIT))
        raise _StopOperation()

    return probe


def _install(app, probe):
    irm = install_manager.InstallRepositoryManager.__new__(install_manager.InstallRepositoryManager)
    irm.app = app
    with mock.patch.object(
        install_manager.InstallRepositoryManager,
        "_InstallRepositoryManager__get_install_info_from_tool_shed",
        side_effect=probe,
    ):
        irm.install("https://toolshed.example.org", "name", "owner", "abc", {})


def _installed_repository_manager(app):
    irm = installed_repository_manager.InstalledRepositoryManager.__new__(
        installed_repository_manager.InstalledRepositoryManager
    )
    irm.app = app
    return irm


def _uninstall(app, probe):
    with mock.patch.object(shed_util_common, "get_tool_panel_config_tool_path_install_dir", probe):
        _installed_repository_manager(app).uninstall_repository(mock.MagicMock(name="repository"))


def _activate(app, probe):
    with mock.patch.object(shed_util_common, "get_tool_panel_config_tool_path_install_dir", probe):
        _installed_repository_manager(app).activate_repository(mock.MagicMock(name="repository"))


def _reset_metadata(app, probe):
    irmm = InstalledRepositoryMetadataManager.__new__(InstalledRepositoryMetadataManager)
    irmm.app = app
    irmm.relative_install_dir = "repos/owner/name/abc"
    irmm.repository = mock.MagicMock(name="repository")
    with mock.patch.object(irmm, "generate_metadata_for_changeset_revision", probe):
        irmm.reset_all_metadata_on_installed_repository()


@pytest.mark.parametrize("operation", [_install, _uninstall, _activate, _reset_metadata])
def test_repository_operation_holds_lock(operation, tmp_path):
    app = mock.MagicMock(name="app")
    app.install_model.engine = create_engine("sqlite://")
    app.config.data_dir = str(tmp_path)
    held: list[bool] = []
    with pytest.raises(_StopOperation):
        operation(app, _probe_lock_then_stop(app, held))
    assert held == [True]
