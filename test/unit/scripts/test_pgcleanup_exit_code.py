"""Tests for pgcleanup.py CLI exit behavior."""

import os
import subprocess
import sys

from galaxy.util import galaxy_directory

SCRIPT = os.path.join(galaxy_directory(), "scripts", "cleanup_datasets", "pgcleanup.py")


def test_exits_nonzero_when_run_sequence_fails(tmp_path):
    # a non-PostgreSQL database makes Cleanup.conn raise inside run()
    config = tmp_path / "galaxy.yml"
    config.write_text(f"galaxy:\n  database_connection: sqlite:///{tmp_path}/galaxy.sqlite\n")
    result = subprocess.run(
        [sys.executable, SCRIPT, "-c", str(config), "--sequence", "purge_deleted_histories", "-l", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, result.stderr
    assert "Caught exception in run sequence" in result.stderr
