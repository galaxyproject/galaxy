"""Regression checks for workspace bootstrap and release lookup."""

import subprocess
from pathlib import Path

import pytest

from galaxy.util import galaxy_directory

ROOT = Path(galaxy_directory())


@pytest.mark.parametrize(
    "path", ["packages/util/src/galaxy/version/__init__.py", "lib/galaxy/version/__init__.py", "lib/galaxy/version.py"]
)
def test_release_version_lookup_across_layouts(tmp_path, path):
    version = tmp_path / path
    version.parent.mkdir(parents=True)
    version.write_text('VERSION_MAJOR = "26.1"\n')
    script = (ROOT / "scripts/release.sh").read_text()
    start = script.index("function galaxy_version_file()")
    end = script.index('\n: "${RELEASE_CURR', start)
    result = subprocess.run(
        ["bash"], input=script[start:end] + "\ngalaxy_version_file\n", cwd=tmp_path, text=True, capture_output=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == path


@pytest.mark.parametrize("fetch_wheels", [0, 1])
def test_workspace_sync_respects_skipped_installation(fetch_wheels):
    script = (ROOT / "scripts/common_startup.sh").read_text()
    start = script.index("sync_workspace_packages() {")
    end = script.index('\n: "${GALAXY_WHEELS_INDEX_URL', start)
    mock = f"uv() {{ echo MOCK_UV; }}\nFETCH_WHEELS={fetch_wheels}\nGALAXY_WORKSPACE_SYNC=1\n"
    result = subprocess.run(["sh"], input=mock + script[start:end], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert ("MOCK_UV" in result.stdout) == bool(fetch_wheels)
