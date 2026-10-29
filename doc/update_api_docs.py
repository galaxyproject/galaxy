"""Generate API pages from the workspace's combined Python namespace tree."""

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apidoc", default="sphinx-apidoc")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "source/lib")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    # Merge namespace portions before scanning so galaxy.rst includes every
    # distribution, rather than being overwritten once per workspace member.
    with tempfile.TemporaryDirectory() as directory:
        sources = Path(directory) / "lib"
        sources.mkdir()
        for member in sorted((root / "packages").glob("*/src")):
            for source in member.rglob("*.py"):
                relative = source.relative_to(member)
                if any(part in {"build", "__pycache__", "node_modules"} for part in relative.parts):
                    continue
                target = sources / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(source.resolve())
        # Mark top-level namespace packages for apidoc's directory scan. These
        # temporary markers do not alter the installed namespace packages.
        for namespace in sources.iterdir():
            if namespace.is_dir() and not (namespace / "__init__.py").exists():
                (namespace / "__init__.py").touch()
        output = Path(directory) / "output"
        subprocess.run(
            [args.apidoc, "-M", "--force", "-o", str(output), str(sources)],
            check=True,
        )
        # Replace existing pages only after generation succeeds.
        if args.output.exists():
            shutil.rmtree(args.output)
        shutil.copytree(output, args.output)


if __name__ == "__main__":
    main()
