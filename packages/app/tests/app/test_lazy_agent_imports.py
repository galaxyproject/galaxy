import subprocess
import sys


def test_import_galaxy_app_does_not_load_pydantic_ai():
    # The installed workspace supplies galaxy.app, so no PYTHONPATH injection is needed.
    code = "import sys, galaxy.app; print('pydantic_ai' in sys.modules)"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "False"
