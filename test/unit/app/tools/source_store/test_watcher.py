"""Unit tests for the tool source store freshness watcher."""

from galaxy.tools.source_store.sqlalchemy import SqlAlchemyToolSourceStore
from galaxy.tools.source_store.watcher import ToolSourceStoreWatcher


def _watched_store(tmp_path, current):
    return SqlAlchemyToolSourceStore(
        url=f"sqlite:///{tmp_path}/store.sqlite",
        read_only=True,
        freshness_probe=lambda: current["token"],
    )


def test_first_check_baselines_without_firing(tmp_path):
    current = {"token": "cvmfs:r:1"}
    fired: list[list[str]] = []
    watcher = ToolSourceStoreWatcher(
        members=[("cvmfs", _watched_store(tmp_path, current))], interval=60, on_change=fired.append
    )
    assert watcher.check() == []
    assert fired == []


def test_token_transition_fires_once(tmp_path):
    current = {"token": "cvmfs:r:1"}
    fired: list[list[str]] = []
    watcher = ToolSourceStoreWatcher(
        members=[("cvmfs", _watched_store(tmp_path, current))], interval=60, on_change=fired.append
    )
    watcher.check()
    current["token"] = "cvmfs:r:2"
    assert watcher.check() == ["cvmfs"]
    assert fired == [["cvmfs"]]
    # Stable at the new revision: no re-fire.
    assert watcher.check() == []
    assert fired == [["cvmfs"]]


def test_probe_failure_neither_fires_nor_clears_baseline(tmp_path):
    current: dict[str, str | None] = {"token": "cvmfs:r:1"}
    fired: list[list[str]] = []

    def probe() -> str:
        token = current["token"]
        if token is None:
            raise OSError("repo unmounted")
        return token

    store = SqlAlchemyToolSourceStore(url=f"sqlite:///{tmp_path}/store.sqlite", read_only=True, freshness_probe=probe)
    watcher = ToolSourceStoreWatcher(members=[("cvmfs", store)], interval=60, on_change=fired.append)
    watcher.check()
    current["token"] = None
    assert watcher.check() == []
    # Probe recovers at the same revision: still no spurious fire.
    current["token"] = "cvmfs:r:1"
    assert watcher.check() == []
    current["token"] = "cvmfs:r:2"
    assert watcher.check() == ["cvmfs"]
    assert fired == [["cvmfs"]]
