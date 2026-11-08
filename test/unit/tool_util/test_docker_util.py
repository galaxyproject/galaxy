import os
import shutil
import subprocess
from pathlib import Path

import pytest

from galaxy.tool_util.deps.docker_util import (
    build_docker_cache_command,
    DEFAULT_PULL_ATTEMPTS,
)

IMAGE = "quay.io/biocontainers/python:3.7--1"

# Records each call; `pull` fails until it has been called $PULL_FAILURES + 1 times,
# and `inspect` succeeds once a pull has succeeded.
STUB_DOCKER = """#!/bin/sh
echo "$*" >> "$STUB_DIR/docker_calls"
case "$1" in
    inspect)
        [ -e "$STUB_DIR/pulled" ]
        ;;
    pull)
        failures=$(grep -c '^pull ' "$STUB_DIR/docker_calls")
        if [ "$failures" -le "$PULL_FAILURES" ]; then
            echo "Pulling from $2"
            echo "short read: unexpected EOF (attempt $failures)" >&2
            exit 1
        fi
        touch "$STUB_DIR/pulled"
        ;;
esac
"""

# Records the requested delay instead of sleeping.
STUB_SLEEP = """#!/bin/sh
echo "$*" >> "$STUB_DIR/sleep_calls"
"""

SHELLS = [shell for shell in ("sh", "bash") if shutil.which(shell)]


def _write_stub(path: Path, contents: str) -> None:
    path.write_text(contents)
    path.chmod(0o755)


def _run_cache_command(tmp_path: Path, shell: str, pull_failures: int, cached: bool = False):
    _write_stub(tmp_path / "docker", STUB_DOCKER)
    _write_stub(tmp_path / "sleep", STUB_SLEEP)
    if cached:
        (tmp_path / "pulled").touch()
    env = dict(
        os.environ,
        PATH=f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
        STUB_DIR=str(tmp_path),
        PULL_FAILURES=str(pull_failures),
    )
    script = f"{build_docker_cache_command(IMAGE)}echo cache command done\n"
    return subprocess.run([shell, "-c", script], env=env, capture_output=True, text=True)


def _lines(path: Path):
    return path.read_text().splitlines() if path.exists() else []


@pytest.mark.parametrize("shell", SHELLS)
def test_cache_command_retries_failed_pull(tmp_path, shell):
    result = _run_cache_command(tmp_path, shell, pull_failures=DEFAULT_PULL_ATTEMPTS - 1)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "cache command done\n"
    # A pull that eventually succeeds must leave the job's stderr clean.
    assert result.stderr == ""
    assert (tmp_path / "pulled").exists()
    pulls = [call for call in _lines(tmp_path / "docker_calls") if call.startswith("pull ")]
    assert pulls == [f"pull {IMAGE}"] * DEFAULT_PULL_ATTEMPTS
    assert _lines(tmp_path / "sleep_calls") == ["5", "10"]


@pytest.mark.parametrize("shell", SHELLS)
def test_cache_command_reports_last_failed_pull(tmp_path, shell):
    result = _run_cache_command(tmp_path, shell, pull_failures=DEFAULT_PULL_ATTEMPTS)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "cache command done\n"
    assert result.stderr == f"Pulling from {IMAGE}\nshort read: unexpected EOF (attempt {DEFAULT_PULL_ATTEMPTS})\n"
    assert not (tmp_path / "pulled").exists()
    pulls = [call for call in _lines(tmp_path / "docker_calls") if call.startswith("pull ")]
    assert len(pulls) == DEFAULT_PULL_ATTEMPTS


@pytest.mark.parametrize("shell", SHELLS)
def test_cache_command_skips_pull_for_cached_image(tmp_path, shell):
    result = _run_cache_command(tmp_path, shell, pull_failures=0, cached=True)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert _lines(tmp_path / "docker_calls") == [f"inspect {IMAGE}"]
    assert _lines(tmp_path / "sleep_calls") == []
