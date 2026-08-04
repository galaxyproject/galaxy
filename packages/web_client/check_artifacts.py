"""Check built distributions for compiled web client assets."""

import argparse
import sys
import tarfile
import zipfile
from pathlib import Path

SDIST_PREFIX = "src/galaxy/web_client"
WHEEL_PREFIX = "galaxy/web_client"


def sdist_members(path: Path) -> list[str]:
    """Return sdist member names relative to the archive's top-level directory."""
    with tarfile.open(path, "r:*") as tar:
        names = tar.getnames()
    # Strip the archive's top-level directory.
    return [name.split("/", 1)[1] for name in names if "/" in name]


def wheel_members(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        return zf.namelist()


def check_members(members: list[str], prefix: str, description: str) -> list[str]:
    errors = []
    build_hash = f"{prefix}/client_build_hash.txt"
    if build_hash not in members:
        errors.append(f"{description} is missing {build_hash}")
    client_dir = f"{prefix}/dist/"
    # Ignore directory-only archive entries.
    if not any(member.startswith(client_dir) and not member.endswith("/") for member in members):
        errors.append(f"{description} contains no files under {client_dir}")
    return errors


def check_artifact(path: Path) -> list[str]:
    if path.name.endswith(".whl"):
        return check_members(wheel_members(path), WHEEL_PREFIX, f"wheel {path.name}")
    if path.name.endswith(".tar.gz"):
        return check_members(sdist_members(path), SDIST_PREFIX, f"sdist {path.name}")
    return []


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", metavar="PATH", nargs="+", help="Built artifacts (or directories containing them)")
    args = parser.parse_args(argv)

    artifacts = []
    for raw_path in args.paths:
        path = Path(raw_path)
        if path.is_dir():
            artifacts.extend(sorted(p for p in path.iterdir() if p.name.endswith((".whl", ".tar.gz"))))
        else:
            artifacts.append(path)

    checked = 0
    errors = []
    for artifact in artifacts:
        artifact_errors = check_artifact(artifact)
        if artifact.name.endswith((".whl", ".tar.gz")):
            checked += 1
        errors.extend(artifact_errors)

    if not checked:
        print(f"ERROR: no sdist or wheel found in: {' '.join(args.paths)}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(
            "ERROR: the built web client is missing from the artifacts above; "
            "`make dist` must run before packaging and MANIFEST.in must list the generated files.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: {checked} artifact(s) contain the compiled web client and its build hash.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
