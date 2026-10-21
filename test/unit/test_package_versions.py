"""Release version updates must validate every manifest before writing any."""

import importlib.util
from pathlib import Path

import pytest
from packaging.version import InvalidVersion

from galaxy.util import galaxy_directory

spec = importlib.util.spec_from_file_location(
    "set_package_versions", Path(galaxy_directory()) / "scripts/set_package_versions.py"
)
assert spec and spec.loader
version_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(version_script)


def test_update_package_versions(tmp_path):
    for name in ("app", "util", "meta"):
        manifest = tmp_path / "packages" / name / "pyproject.toml"
        manifest.parent.mkdir(parents=True)
        manifest.write_text('[project]\nname = "example"\nversion = "26.1.dev0"\n\n[tool.example]\nversion = "keep"\n')
    version_script.set_package_versions(tmp_path, "26.2.dev0")
    for manifest in tmp_path.glob("packages/*/pyproject.toml"):
        assert 'version = "26.2.dev0"' in manifest.read_text()
        assert 'version = "keep"' in manifest.read_text()


def test_invalid_manifest_leaves_all_manifests_unchanged(tmp_path):
    valid = tmp_path / "packages/app/pyproject.toml"
    invalid = tmp_path / "packages/util/pyproject.toml"
    for manifest in (valid, invalid):
        manifest.parent.mkdir(parents=True)
    contents = '[project]\nversion = "26.1.dev0"\n'
    valid.write_text(contents)
    invalid.write_text('[project]\nname = "missing-version"\n')
    with pytest.raises(ValueError, match="static project version"):
        version_script.set_package_versions(tmp_path, "26.2.dev0")
    assert valid.read_text() == contents


def test_invalid_version_is_rejected(tmp_path):
    with pytest.raises(InvalidVersion):
        version_script.set_package_versions(tmp_path, "invalid version")
