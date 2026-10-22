import os
import subprocess
import sys
from pathlib import Path

from galaxy import version


def test_import_galaxy_app_does_not_load_pydantic_ai():
    lib_dir = str(Path(version.__file__).resolve().parents[2])
    code = "import sys, galaxy.app; print('pydantic_ai' in sys.modules)"
    env = {**os.environ, "PYTHONPATH": lib_dir}
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "False"
