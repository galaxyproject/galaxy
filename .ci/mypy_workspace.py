"""Supply mypy's namespace roots from the uv workspace configuration."""

import os
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # mypy's TOML reader on Python 3.10

ROOT = Path(__file__).resolve().parents[1]


def members(root: Path) -> list[Path]:
    with (root / "pyproject.toml").open("rb") as handle:
        workspace = tomllib.load(handle)["tool"]["uv"]["workspace"]
    members = {path for pattern in workspace["members"] for path in root.glob(pattern)}
    excluded = {path for pattern in workspace.get("exclude", []) for path in root.glob(pattern)}
    return sorted(members - excluded)


def source_roots(root: Path) -> list[str]:
    return [str(path / "src") for path in members(root) if (path / "src").is_dir()] + [str(root / "test")]


def targets(root: Path) -> list[str]:
    return source_roots(root) + [str(path / "tests") for path in members(root) if (path / "tests").is_dir()]


def environment(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    roots = source_roots(root)
    if env.get("MYPYPATH"):
        roots.append(env["MYPYPATH"])
    env["MYPYPATH"] = os.pathsep.join(roots)
    return env


if __name__ == "__main__":
    sys.exit(
        subprocess.call([sys.executable, "-m", "mypy", *sys.argv[1:], *targets(ROOT)], cwd=ROOT, env=environment(ROOT))
    )
