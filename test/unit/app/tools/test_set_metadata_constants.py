"""Guards for the import surface of galaxy.metadata.set_metadata.

set_metadata runs as a separate process for every finished job. On installations
where the Galaxy tree lives on a shared filesystem, the cost of importing this
module is paid once per job and is dominated by how many modules it drags in, so
the import surface is a correctness-adjacent property worth pinning down.
"""

import subprocess
import sys

import pytest


def test_command_version_filename_matches_pulsar():
    """The inlined constant must stay in sync with pulsar's definition.

    set_metadata defines COMMAND_VERSION_FILENAME itself rather than importing it
    from pulsar.client.staging, to avoid pulling in the job runner and tool
    framework. That is only safe while both agree on the value.
    """
    pulsar_staging = pytest.importorskip("pulsar.client.staging")

    from galaxy.metadata.set_metadata import COMMAND_VERSION_FILENAME

    assert COMMAND_VERSION_FILENAME == pulsar_staging.COMMAND_VERSION_FILENAME


def test_set_metadata_does_not_import_tool_framework():
    """Importing set_metadata must not drag in the tool or job runner framework.

    Runs in a subprocess because the modules may already be imported in the
    pytest process by unrelated tests.
    """
    unwanted = [
        "galaxy.tools",
        "galaxy.jobs.runners",
        "galaxy.tool_util.cwl.parser",
        "galaxy.tool_shed.util.repository_util",
    ]
    program = (
        "import sys\n"
        "import galaxy.metadata.set_metadata\n"
        f"unwanted = {unwanted!r}\n"
        "print(','.join(m for m in unwanted if m in sys.modules))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True, check=True
    )
    leaked = [m for m in result.stdout.strip().split(",") if m]
    assert not leaked, f"set_metadata should not import: {', '.join(leaked)}"
