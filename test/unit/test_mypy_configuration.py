"""Exercise workspace type checking across split namespace packages."""

import configparser
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    pytest.importorskip("mypy")
    root = tmp_path / "workspace with spaces"
    files = {
        "packages/util/src/galaxy/util/__init__.py": "def answer() -> int:\n    return 42\n",
        "packages/config/src/galaxy/config/__init__.py": "from galaxy.util import answer\nvalue: str = answer()\n",
        "packages/util/tests/test_util.py": "def test_util() -> None:\n    pass\n",
        "packages/config/tests/test_config.py": "def test_config() -> None:\n    pass\n",
        "test/unit/test_example.py": "def test_example() -> None:\n    pass\n",
    }
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    config = configparser.ConfigParser(interpolation=None)
    config.read(ROOT / "mypy.ini")
    fixture_config = configparser.ConfigParser(interpolation=None)
    fixture_config["mypy"] = {name: config["mypy"][name] for name in ("explicit_package_bases",)}
    with (root / "mypy.ini").open("w") as handle:
        fixture_config.write(handle)
    (root / "pyproject.toml").write_text(
        '[tool.uv.workspace]\nmembers = ["packages/*"]\nexclude = ["packages/excluded"]\n'
    )
    excluded = root / "packages/excluded/src/invalid.py"
    excluded.parent.mkdir(parents=True)
    excluded.write_text("invalid syntax!\n")
    adapter = root / ".ci/mypy_workspace.py"
    adapter.parent.mkdir()
    adapter.write_text((ROOT / ".ci/mypy_workspace.py").read_text())
    monkeypatch.syspath_prepend(str(ROOT / ".ci"))
    monkeypatch.delenv("MYPYPATH", raising=False)
    monkeypatch.chdir(root)
    return root


@pytest.mark.parametrize("has_error", [True, False])
def test_workspace_mypy_checks_cross_package_imports(workspace, has_error):
    if not has_error:
        source = workspace / "packages/config/src/galaxy/config/__init__.py"
        source.write_text(source.read_text().replace("value: str", "value: int"))
    result = subprocess.run(
        [
            sys.executable,
            str(workspace / ".ci/mypy_workspace.py"),
            "--no-incremental",
            "--no-site-packages",
            "--output",
            "json",
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == int(has_error), result.stdout + result.stderr
    errors = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
    assert [error["code"] for error in errors] == (["assignment"] if has_error else [])


def test_exemption_checker_preserves_config_relative_paths(workspace, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / ".ci"))
    checker = importlib.import_module("check_mypy_legacy_list")
    config = workspace / "mypy.ini"
    with config.open("a") as handle:
        handle.write("disallow_untyped_defs = True\n\n[mypy-galaxy.config]\ndisallow_untyped_defs = False\n")
    source = workspace / "packages/config/src/galaxy/config/__init__.py"
    source.write_text("def bad():\n    return 42\n")
    monkeypatch.setattr(checker, "ROOT", str(workspace))
    monkeypatch.setattr(checker, "MYPY_INI", str(config))
    monkeypatch.setattr(sys, "argv", ["check_mypy_legacy_list.py", "--cache-dir", str(workspace / "cache")])
    assert checker.main() == 0
