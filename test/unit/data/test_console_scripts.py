"""Load every console script that galaxy-data declares."""

import tomllib
from importlib.metadata import EntryPoint
from pathlib import Path

import pytest

# Resolve through packages/data/tests/data, which links to this directory.
PYPROJECT = Path(__file__).resolve().parents[3] / "packages" / "data" / "pyproject.toml"
SCRIPTS = tomllib.loads(PYPROJECT.read_text())["project"]["scripts"]


@pytest.mark.parametrize("name", sorted(SCRIPTS))
def test_console_script_loads(name):
    assert callable(EntryPoint(name=name, group="console_scripts", value=SCRIPTS[name]).load())
