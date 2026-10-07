#!/usr/bin/env python
"""Select Galaxy sources for ty, including symlinked package directories."""

import argparse
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDED = (
    "unittest_utils/functional_tools",
    "test/functional/tools/cwl_tools",
    "tool_shed/test/test_data/repos",
)


def python_files(directory: Path, *, followlinks: bool = False) -> list[Path]:
    def raise_error(error: OSError) -> None:
        raise error

    files = []
    for current, directories, names in os.walk(directory, followlinks=followlinks, onerror=raise_error):
        directories[:] = [name for name in directories if name != "build"]
        if any(part in Path(current).as_posix() for part in EXCLUDED):
            directories.clear()
            continue
        files.extend(Path(current) / name for name in sorted(names) if name.endswith(".py"))
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--package", type=Path)
    args, ty_args = parser.parse_known_args()
    if args.package:
        package = args.package.resolve()
        if not package.is_dir() or not (package / "src").is_dir():
            parser.error(f"not a Galaxy package with a src directory: {package}")
        directories = [package / "src"]
        if (package / "tests").is_dir():
            directories.append(package / "tests")
        files = [path.resolve() for directory in directories for path in python_files(directory, followlinks=True)]
    else:
        files = [path for directory in (ROOT / "lib", ROOT / "test") for path in python_files(directory)]
        files.extend(python_files(ROOT / "lib/galaxy/tools/bundled", followlinks=True))
    if not files:
        parser.error("no Python files found")
    config = os.environ.get("TY_CHECK_CONFIG_FILE")
    if config:
        ty_args = ["--config-file", config, *ty_args]
    return subprocess.call(
        [os.environ.get("TY", "ty"), "check", *ty_args, *sorted({os.path.relpath(path, ROOT) for path in files})],
        cwd=ROOT,
    )


if __name__ == "__main__":
    raise SystemExit(main())
