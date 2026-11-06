import os
import subprocess

import pytest

from galaxy.jobs.runners.util.job_script import (
    MEMORY_STATEMENT_DEFAULT_TEMPLATE,
    PREPARE_DIRS_TEMPLATE,
)
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


def test_memory_floor_never_exceeds_allocation(tmp_path):
    environment = _memory_environment(
        tmp_path,
        GALAXY_MEMORY_MB="128",
        GALAXY_MEMORY_MB_OVERHEAD="64",
    )

    assert environment == {
        "GALAXY_MEMORY_MB": "128",
        "GALAXY_MEMORY_MB_PER_SLOT": "32",
        "GALAXY_MEMORY_GB": "",
        "GALAXY_MEMORY_GB_PER_SLOT": "",
    }


def test_memory_gb_variables_are_available_to_containers():
    assert "GALAXY_MEMORY_GB" in ToolInfo().env_pass_through
    assert "GALAXY_MEMORY_GB_PER_SLOT" in ToolInfo().env_pass_through


def _run_prepare_dirs(job_directory):
    subprocess.run(["bash", "-c", PREPARE_DIRS_TEMPLATE.format(working_directory=job_directory)], capture_output=True)


def _tree(directory):
    return {str(path.relative_to(directory)): path.read_bytes() for path in directory.rglob("*") if path.is_file()}


def test_prepare_dirs_restores_backup_only_created_after_successful_copy(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root can read files without read permission")
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "registry.xml").write_text("<registry/>")
    unreadable = configs / "unreadable"
    unreadable.write_text("secret")
    unreadable.chmod(0)

    _run_prepare_dirs(tmp_path)
    assert not (tmp_path / "_configs").exists()

    unreadable.chmod(0o600)
    _run_prepare_dirs(tmp_path)
    assert _tree(tmp_path / "_configs") == _tree(configs)

    expected = _tree(configs)
    (configs / "registry.xml").write_text("")
    _run_prepare_dirs(tmp_path)
    assert _tree(configs) == expected


def test_prepare_dirs_skips_backup_when_stale_partial_cannot_be_removed(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root can remove files from read-only directories")
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "registry.xml").write_text("<registry/>")
    expected = _tree(configs)
    stale = tmp_path / "_configs.partial" / "sub"
    stale.mkdir(parents=True)
    (stale / "f").write_text("stale")
    stale.chmod(0o555)

    _run_prepare_dirs(tmp_path)
    for path in tmp_path.rglob("sub"):
        path.chmod(0o755)

    assert not (tmp_path / "_configs").exists()
    assert _tree(configs) == expected
