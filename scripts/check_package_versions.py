#!/usr/bin/env python3
"""Dry-run contract check: package versions match the intended Galaxy version.

Check steps (equivalent manual procedure):
  1. Read the intended version from the canonical version file,
     ``packages/util/src/galaxy/version/__init__.py`` (fallback:
     ``packages/util/src/galaxy/version/__init__.py`` during migration).
  2. For each ``packages/*/pyproject.toml``, compare its ``version`` field
     against the intended version and report drift.
  3. For each built wheel in ``packages/*/dist/*.whl`` (if any), read the
     ``Version:`` field from its ``*.dist-info/METADATA`` and compare it
     against that package's ``pyproject.toml`` version.

Usage:
    python scripts/check_package_versions.py [--strict] [--galaxy-root PATH]

Exit status is 0 in dry-run (report-only) mode. With ``--strict``, exit 2
if any manifest or wheel-metadata drift is found (intended for CI once
versions are reconciled).
"""

import argparse
import glob
import os
import re
import sys
import zipfile

VERSION_MAJOR_RE = re.compile(r'^VERSION_MAJOR\s*=\s*["\']([^"\']*)["\']', flags=re.MULTILINE)
VERSION_MINOR_RE = re.compile(r'^VERSION_MINOR\s*=\s*["\']([^"\']*)["\']', flags=re.MULTILINE)
PROJECT_VERSION_RE = re.compile(r'^version\s*=\s*"?([^"\s]+)"?', flags=re.MULTILINE)
WHEEL_METADATA_VERSION_RE = re.compile(r"^Version:\s*(.+)$", flags=re.MULTILINE)


def version_file(galaxy_root):
    # Canonical location first, legacy lib/ fallback during migration.
    for rel in (
        os.path.join("packages", "util", "src", "galaxy", "version", "__init__.py"),
        os.path.join("packages", "util", "src", "galaxy", "version", "__init__.py"),
    ):
        path = os.path.join(galaxy_root, rel)
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"No galaxy version file found under {galaxy_root}")


def read_root_version(path):
    with open(path) as f:
        contents = f.read()
    major = VERSION_MAJOR_RE.search(contents).group(1)
    minor = VERSION_MINOR_RE.search(contents).group(1)
    return major + (f".{minor}" if minor else "")


def read_project_version(pyproject_path):
    with open(pyproject_path) as f:
        contents = f.read()
    match = PROJECT_VERSION_RE.search(contents)
    return match.group(1) if match else None


def read_wheel_versions(dist_dir):
    versions = {}
    for whl in sorted(glob.glob(os.path.join(dist_dir, "*.whl"))):
        with zipfile.ZipFile(whl) as zf:
            metadata_names = [n for n in zf.namelist() if n.endswith(".dist-info/METADATA")]
            if not metadata_names:
                versions[os.path.basename(whl)] = None
                continue
            metadata = zf.read(metadata_names[0]).decode("utf-8", "replace")
        match = WHEEL_METADATA_VERSION_RE.search(metadata)
        versions[os.path.basename(whl)] = match.group(1).strip() if match else None
    return versions


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="exit 2 on any drift")
    parser.add_argument("--galaxy-root", default=os.getcwd(), help="galaxy repository root")
    args = parser.parse_args(argv)

    galaxy_root = args.galaxy_root
    vfile = version_file(galaxy_root)
    intended = read_root_version(vfile)
    print(f"intended version: {intended} (from {os.path.relpath(vfile, galaxy_root)})")

    drift = []
    for pyproject in sorted(glob.glob(os.path.join(galaxy_root, "packages", "*", "pyproject.toml"))):
        package = os.path.basename(os.path.dirname(pyproject))
        if package == "packages":
            continue
        manifest_version = read_project_version(pyproject)
        status = "ok" if manifest_version == intended else "DRIFT"
        if manifest_version != intended:
            drift.append((package, "manifest", manifest_version, intended))
        print(f"package {package:<20} manifest={manifest_version:<12} intended={intended:<12} {status}")
        for wheel, wheel_version in read_wheel_versions(os.path.join(os.path.dirname(pyproject), "dist")).items():
            wstatus = "ok" if wheel_version == manifest_version else "DRIFT"
            if wheel_version != manifest_version:
                drift.append((package, wheel, wheel_version, manifest_version))
            print(f"    wheel {wheel:<40} metadata={wheel_version:<12} {wstatus}")

    if drift:
        print(f"\ndrift found in {len(drift)} location(s):")
        for package, where, found, expected in drift:
            print(f"  {package} [{where}]: found {found}, expected {expected}")
        return 2 if args.strict else 0
    print("\nno drift found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
