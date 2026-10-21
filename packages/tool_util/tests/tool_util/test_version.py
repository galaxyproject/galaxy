import pytest
from packaging.version import Version

from galaxy.tool_util.version import (
    LegacyVersion,
    parse_version,
)

# This list must be in the correct sorting order
VERSIONS = [
    # Implicit epoch of 0
    "1.0.dev456",
    "1.0a1",
    "1.0a2.dev456",
    "1.0a12.dev456",
    "1.0a12",
    "1.0b1.dev456",
    "1.0b2",
    "1.0b2.post345.dev456",
    "1.0b2.post345",
    "1.0b2-346",
    "1.0c1.dev456",
    "1.0c1",
    "1.0rc2",
    "1.0c3",
    "1.0",
    "1.0.post456.dev34",
    "1.0.post456",
    "1.1.dev1",
    "1.2+123abc",
    "1.2+123abc456",
    "1.2+abc",
    "1.2+abc123",
    "1.2+abc123def",
    "1.2+1234.abc",
    "1.2+123456",
    "1.2.r32+123456",
    "1.2.rev33+123456",
    # Explicit epoch of 1
    "1!1.0.dev456",
    "1!1.0a1",
    "1!1.0a2.dev456",
    "1!1.0a12.dev456",
    "1!1.0a12",
    "1!1.0b1.dev456",
    "1!1.0b2",
    "1!1.0b2.post345.dev456",
    "1!1.0b2.post345",
    "1!1.0b2-346",
    "1!1.0c1.dev456",
    "1!1.0c1",
    "1!1.0rc2",
    "1!1.0c3",
    "1!1.0",
    "1!1.0.post456.dev34",
    "1!1.0.post456",
    "1!1.1.dev1",
    "1!1.2+123abc",
    "1!1.2+123abc456",
    "1!1.2+abc",
    "1!1.2+abc123",
    "1!1.2+abc123def",
    "1!1.2+1234.abc",
    "1!1.2+123456",
    "1!1.2.r32+123456",
    "1!1.2.rev33+123456",
]

LEGACY_VERSIONS = ["foobar", "a cat is fine too", "lolwut", "1.8.1+2+galaxy0"]


@pytest.mark.parametrize("version", VERSIONS)
def test_parse_pep440_versions(version: str) -> None:
    assert isinstance(parse_version(version), Version)


@pytest.mark.parametrize("version", LEGACY_VERSIONS)
def test_legacy_version_fields(version: str) -> None:
    parsed_version = parse_version(version)
    assert isinstance(parsed_version, LegacyVersion)
    assert parsed_version.public == version
    assert parsed_version.base_version == version
    assert parsed_version.epoch == -1
    assert parsed_version.release is None
    assert parsed_version.pre is None
    assert parsed_version.post is None
    assert parsed_version.dev is None
    assert parsed_version.local is None
    assert parsed_version.is_prerelease is False
    assert parsed_version.is_postrelease is False
    assert parsed_version.is_devrelease is False


@pytest.mark.parametrize(
    "lower_ver,greater_ver",
    [(VERSIONS[i], VERSIONS[i + 1]) for i in range(len(VERSIONS) - 1)]
    + [(lv, v) for v in VERSIONS for lv in LEGACY_VERSIONS],
)
def test_version_cmp(lower_ver: str, greater_ver: str) -> None:
    assert parse_version(lower_ver) < parse_version(greater_ver)
