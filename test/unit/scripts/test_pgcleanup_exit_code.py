"""Tests for pgcleanup.py CLI exit behavior."""

import importlib.util
import os

import pytest

from galaxy.util import galaxy_directory


def _load_pgcleanup_module():
    script_path = os.path.join(galaxy_directory(), "scripts", "cleanup_datasets", "pgcleanup.py")
    spec = importlib.util.spec_from_file_location("pgcleanup_exit_code_test", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_main_exits_nonzero_when_run_raises(monkeypatch):
    pgcleanup = _load_pgcleanup_module()

    class BrokenCleanup:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def run(self):
            raise RuntimeError("simulated pgcleanup failure")

    monkeypatch.setattr(pgcleanup, "Cleanup", BrokenCleanup)

    with pytest.raises(SystemExit) as exc_info:
        pgcleanup.main()

    assert exc_info.value.code == 1
