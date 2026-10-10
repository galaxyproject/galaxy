"""Mapping between conda platforms (subdirs) and OCI/Singularity architecture names."""

import logging
import platform as _platform
import re
from typing import Any

log = logging.getLogger(__name__)

_SUBDIR_TO_OCI_ARCH = {
    "linux-64": "amd64",
    "linux-aarch64": "arm64",
    "linux-ppc64le": "ppc64le",
    "linux-s390x": "s390x",
    "linux-riscv64": "riscv64",
    "osx-arm64": "arm64",
    "osx-64": "amd64",
}

_MACHINE_TO_OCI_ARCH = {
    "x86_64": "amd64",
    "amd64": "amd64",
    "aarch64": "arm64",
    "arm64": "arm64",
    "ppc64le": "ppc64le",
    "s390x": "s390x",
    "riscv64": "riscv64",
}

_SAFE_SUBDIR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def platform_to_oci_arch(subdir: str | None) -> str | None:
    """Return the OCI architecture name for a conda subdir, or ``None`` if unknown.

    >>> platform_to_oci_arch("linux-aarch64")
    'arm64'
    >>> platform_to_oci_arch("win-64") is None
    True
    """
    if not subdir:
        return None
    return _SUBDIR_TO_OCI_ARCH.get(subdir)


def server_oci_arch() -> str | None:
    """OCI architecture name of the machine running this process."""
    return _MACHINE_TO_OCI_ARCH.get(_platform.machine().lower())


def destination_platform(destination_info: dict[str, Any] | None) -> str | None:
    """Return the usable ``platform`` of a job destination, or ``None``.

    The value becomes a directory name in the image cache, so anything that is not a plain name is ignored.
    """
    platform = (destination_info or {}).get("platform")
    if not platform:
        return None
    platform = str(platform)
    if not _SAFE_SUBDIR.match(platform):
        log.warning("Ignoring destination platform '%s' for container resolution: not a valid platform name", platform)
        return None
    return platform


def pull_arch(platform: str | None) -> str | None:
    """OCI architecture to request when pulling for ``platform``, ``None`` if the server's own architecture applies."""
    arch = platform_to_oci_arch(platform)
    if arch is None or arch == server_oci_arch():
        return None
    return arch
