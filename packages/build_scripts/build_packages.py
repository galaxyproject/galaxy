"""Build workspace distributions with galaxy-release-util's artifact checks.

Adapt the release tool's fixed lib/ lookups to workspace version and
requirements paths.
"""

import runpy
import sys
from pathlib import Path

from galaxy_release_util.point_release import (
    build_meta_dependencies,
    build_package,
    get_sorted_package_paths,
    Package,
    read_package,
)
from packaging.version import Version


class WorkspacePackage(Package):
    @property
    def pinned_requirements_txt(self) -> Path:
        return self.path.parent / "app/src/galaxy/dependencies/pinned-requirements.txt"


def main(root: Path) -> None:
    version = Version(runpy.run_path(str(root / "packages/util/src/galaxy/version/__init__.py"))["VERSION"])
    packages = [
        WorkspacePackage(path=path, current_version=read_package(path).current_version)
        for path in get_sorted_package_paths(root)
    ]
    for package in packages:
        if package.name == "meta":
            build_meta_dependencies(package, packages, version)
        build_package(package)


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
