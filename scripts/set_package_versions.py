#!/usr/bin/env python3
"""Set every workspace distribution's static project version for a release."""

import re
import sys
from pathlib import Path

from packaging.version import Version


def set_package_versions(root: Path, version: str) -> None:
    Version(version)  # Validate before touching any manifests.
    updates = []
    for manifest in sorted((root / "packages").glob("*/pyproject.toml")):
        contents = manifest.read_text()
        project = re.search(r"(?ms)^\[project\]\n.*?(?=^\[|\Z)", contents)
        if project is None:
            raise ValueError(f"Missing project table: {manifest}")
        table, count = re.subn(r"^version\s*=.*$", f'version = "{version}"', project.group(), flags=re.MULTILINE)
        if count != 1:
            raise ValueError(f"Expected one static project version: {manifest}")
        updates.append((manifest, contents[: project.start()] + table + contents[project.end() :]))
    for manifest, contents in updates:
        manifest.write_text(contents)


if __name__ == "__main__":
    set_package_versions(Path(__file__).resolve().parent.parent, sys.argv[1])
