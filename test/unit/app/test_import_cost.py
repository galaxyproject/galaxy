"""Keep optional runtime dependencies out of the application import graph."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("module", ["galaxy.jobs", "galaxy.app"])
def test_galaxy_app_import_graph(module):
    root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "lib") + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            f"import {module}, json, sys; json.dump(sorted(sys.modules), sys.stdout)",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    modules = json.loads(result.stdout)
    assert "pulsar.client" not in modules
    assert "pydantic_ai" not in modules
    assert "galaxy.agents.base" not in modules
