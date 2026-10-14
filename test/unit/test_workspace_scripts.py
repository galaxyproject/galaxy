"""Regression checks for workspace bootstrap, release lookup, and source links."""

import os
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


@pytest.mark.parametrize(
    "path",
    [
        "packages/util/src/galaxy/util/test/unpackaged.py",
        "packages/data/src/galaxy/datatypes/test/unpackaged.py",
        "packages/app/src/galaxy/tools/bundled",
    ],
)
def test_source_link_check_rejects_aliases_back_into_lib(tmp_path, path):
    env = {**os.environ, "GIT_INDEX_FILE": str(tmp_path / "index")}
    subprocess.run(["git", "read-tree", "HEAD"], cwd=ROOT, env=env, check=True)
    object_id = (
        subprocess.check_output(
            ["git", "hash-object", "-w", "--stdin"], input=b"../../../../../../lib/galaxy/util", cwd=ROOT
        )
        .decode()
        .strip()
    )
    subprocess.run(
        ["git", "update-index", "--add", "--cacheinfo", f"120000,{object_id},{path}"],
        cwd=ROOT,
        env=env,
        check=True,
    )
    result = subprocess.run(["bash", ".ci/check_no_source_links.sh"], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert f"disallowed source link: {path}" in result.stderr
