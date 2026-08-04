"""Regression tests for the contents of the built galaxy-web-client artifacts.

``galaxy-web-client`` exists to ship the compiled frontend.  Both the frontend
(``src/galaxy/web_client/dist``) and ``src/galaxy/web_client/client_build_hash.txt``
are produced by ``make dist`` and are git-ignored, so setuptools-scm's SCM file
finder cannot see them and they only reach the artifacts because MANIFEST.in lists
them explicitly.  When MANIFEST.in was dropped during the "src" layout conversion
the published 26.1.0 wheel shipped without the web client at all, and
``galaxy-web-client-install`` failed on every installation.

These tests build a real sdist and wheel from a copy of the package that has small
sentinel files standing in for the compiled frontend, so they run in seconds
without an npm build.
"""

import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from check_artifacts import check_artifact  # noqa: E402

PACKAGE_DIR = Path(__file__).parent.parent
# Generated, git-ignored, or otherwise irrelevant entries that must not be copied
# into the staging tree -- `dist` in particular covers both the package's own
# build output and the compiled frontend we replace with sentinels.
IGNORED = shutil.ignore_patterns(
    "dist", "build", "*.egg-info", "__pycache__", ".venv", ".tox", ".omc", "client_build_hash.txt", "tests"
)
BUILD_HASH = "0123456789abcdef0123456789abcdef01234567"
SENTINELS = {
    "index.html": "<html>sentinel web client</html>",
    "static/js/app.js": "console.log('sentinel');",
}


def _build_command(out_dir: Path):
    if shutil.which("uv"):
        return ["uv", "build", "-o", str(out_dir)]
    return [sys.executable, "-m", "build", "-o", str(out_dir)]


@pytest.fixture(scope="module")
def artifacts(tmp_path_factory):
    """Build an sdist and a wheel from the package with a sentinel web client staged."""
    tmp_path = tmp_path_factory.mktemp("web_client_packaging")
    source_dir = tmp_path / "web_client"
    # symlinks=False so the LICENSE and dev-requirements.txt symlinks, which point
    # outside the package, are dereferenced into the standalone copy.
    shutil.copytree(PACKAGE_DIR, source_dir, symlinks=False, ignore=IGNORED)

    client_dir = source_dir / "src" / "galaxy" / "web_client"
    (client_dir / "client_build_hash.txt").write_text(f"{BUILD_HASH}\n")
    for relative_path, content in SENTINELS.items():
        sentinel = client_dir / "dist" / relative_path
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text(content)

    out_dir = tmp_path / "dist"
    subprocess.run(_build_command(out_dir), cwd=source_dir, check=True)

    sdists = list(out_dir.glob("*.tar.gz"))
    wheels = list(out_dir.glob("*.whl"))
    assert len(sdists) == 1, f"expected exactly one sdist, got {sdists}"
    assert len(wheels) == 1, f"expected exactly one wheel, got {wheels}"
    return sdists[0], wheels[0]


@pytest.fixture(scope="module")
def sdist_members(artifacts):
    sdist, _ = artifacts
    with tarfile.open(sdist, "r:*") as tar:
        return [name.split("/", 1)[1] for name in tar.getnames() if "/" in name]


@pytest.fixture(scope="module")
def wheel_members(artifacts):
    _, wheel = artifacts
    with zipfile.ZipFile(wheel) as zf:
        return zf.namelist()


def test_sdist_contains_build_hash(sdist_members):
    assert "src/galaxy/web_client/client_build_hash.txt" in sdist_members


def test_sdist_contains_web_client(sdist_members):
    for relative_path in SENTINELS:
        assert f"src/galaxy/web_client/dist/{relative_path}" in sdist_members


def test_wheel_contains_build_hash(artifacts, wheel_members):
    _, wheel = artifacts
    assert "galaxy/web_client/client_build_hash.txt" in wheel_members
    with zipfile.ZipFile(wheel) as zf:
        assert zf.read("galaxy/web_client/client_build_hash.txt").decode().strip() == BUILD_HASH


def test_wheel_contains_web_client(artifacts, wheel_members):
    _, wheel = artifacts
    with zipfile.ZipFile(wheel) as zf:
        for relative_path, content in SENTINELS.items():
            member = f"galaxy/web_client/dist/{relative_path}"
            assert member in wheel_members
            assert zf.read(member).decode() == content


def test_wheel_installs_to_the_path_install_py_expects(artifacts, tmp_path):
    """`galaxy.web_client.install` asserts on this exact layout before doing anything."""
    _, wheel = artifacts
    site_packages = tmp_path / "site-packages"
    with zipfile.ZipFile(wheel) as zf:
        zf.extractall(site_packages)
    assert (site_packages / "galaxy" / "web_client" / "dist").is_dir()


def test_check_artifacts_accepts_the_built_artifacts(artifacts):
    for artifact in artifacts:
        assert check_artifact(artifact) == []
