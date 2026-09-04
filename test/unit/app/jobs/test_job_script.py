import os
import subprocess

from galaxy.jobs.runners.util.job_script import MEMORY_STATEMENT_DEFAULT_TEMPLATE
from galaxy.tool_util.deps.dependencies import ToolInfo

MEMORY_VARIABLES = (
    "GALAXY_MEMORY_MB",
    "GALAXY_MEMORY_MB_PER_SLOT",
    "GALAXY_MEMORY_GB",
    "GALAXY_MEMORY_GB_PER_SLOT",
)


def _memory_environment(tmp_path, **values):
    script = MEMORY_STATEMENT_DEFAULT_TEMPLATE.safe_substitute(metadata_directory=tmp_path)
    script += "\n" + "\n".join(f'printf "{name}=%s\\n" "${{{name}-}}"' for name in MEMORY_VARIABLES)
    environment = {"PATH": os.environ["PATH"], "GALAXY_SLOTS": "4", **values}

    completed = subprocess.run(
        ["bash", "-c", script],
        check=True,
        capture_output=True,
        env=environment,
        text=True,
    )
    return dict(line.split("=", 1) for line in completed.stdout.splitlines())


def test_memory_gb_variables_are_derived_from_total_memory(tmp_path):
    environment = _memory_environment(tmp_path, GALAXY_MEMORY_MB="8192")

    assert environment == {
        "GALAXY_MEMORY_MB": "8192",
        "GALAXY_MEMORY_MB_PER_SLOT": "2048",
        "GALAXY_MEMORY_GB": "8",
        "GALAXY_MEMORY_GB_PER_SLOT": "2",
    }


def test_memory_overhead_applies_to_per_slot_input(tmp_path):
    environment = _memory_environment(
        tmp_path,
        GALAXY_MEMORY_MB_PER_SLOT="4096",
        GALAXY_MEMORY_MB_OVERHEAD="2048",
        GALAXY_MEMORY_MB_FLOOR="1024",
    )

    assert environment == {
        "GALAXY_MEMORY_MB": "14336",
        "GALAXY_MEMORY_MB_PER_SLOT": "3584",
        "GALAXY_MEMORY_GB": "14",
        "GALAXY_MEMORY_GB_PER_SLOT": "3",
    }


def test_memory_floor_and_sub_gb_values(tmp_path):
    environment = _memory_environment(
        tmp_path,
        GALAXY_MEMORY_MB="2048",
        GALAXY_MEMORY_MB_OVERHEAD="1536",
        GALAXY_MEMORY_MB_FLOOR="1024",
    )

    assert environment == {
        "GALAXY_MEMORY_MB": "1024",
        "GALAXY_MEMORY_MB_PER_SLOT": "256",
        "GALAXY_MEMORY_GB": "1",
        "GALAXY_MEMORY_GB_PER_SLOT": "",
    }


def test_memory_gb_variables_are_available_to_containers():
    assert "GALAXY_MEMORY_GB" in ToolInfo().env_pass_through
    assert "GALAXY_MEMORY_GB_PER_SLOT" in ToolInfo().env_pass_through
