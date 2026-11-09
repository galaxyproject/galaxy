from unittest import mock

import pytest

from galaxy.jobs.runners.slurm import (
    MEMORY_LIMIT_MESSAGES,
    OUT_OF_MEMORY_MSG,
    PROBABLY_OUT_OF_MEMORY_MSG,
)
from galaxy.jobs.runners.util.slurm import (
    check_memory_limit,
    MEMORY_LIMIT_EXCEEDED,
    MEMORY_LIMIT_PROBABLY_EXCEEDED,
    NOT_FOUND,
    slurm_job_state,
)
from galaxy.util import commands

INVALID_JOB_ID = "slurm_load_jobs error: Invalid job id specified\n"


def _execute_returning(*outputs):
    return mock.Mock(side_effect=list(outputs))


def _command_error(stderr):
    return commands.CommandLineException("cmd", "", stderr, 1)


def test_parses_job_state_with_values_containing_spaces_and_equals():
    execute = _execute_returning(
        "JobId=7 Comment=** time_limit (60m) min_nodes (1) ** JobState=OUT_OF_MEMORY StdIn=StdIn=/dev/null\n"
    )
    assert slurm_job_state("7", execute=execute) == "OUT_OF_MEMORY"
    execute.assert_called_once_with(["scontrol", "-o", "show", "job", "7"])


def test_passes_cluster_from_slurm_drmaa_job_id():
    execute = _execute_returning("JobState=TIMEOUT\n")
    assert slurm_job_state("7.mycluster", execute=execute) == "TIMEOUT"
    execute.assert_called_once_with(["scontrol", "-o", "-M", "mycluster", "show", "job", "7"])


def test_falls_back_to_sacct_for_old_jobs():
    execute = _execute_returning(_command_error(INVALID_JOB_ID), "CANCELLED by 1000+\nCANCELLED\n")
    assert slurm_job_state("7.mycluster", execute=execute) == "CANCELLED"
    assert execute.call_args.args[0] == ["sacct", "-n", "-o", "state%-32", "-M", "mycluster", "-j", "7"]


def test_not_found_when_accounting_is_disabled():
    execute = _execute_returning(
        _command_error(INVALID_JOB_ID), _command_error("SLURM accounting storage is disabled\n")
    )
    assert slurm_job_state("7", execute=execute) == NOT_FOUND


def test_other_scontrol_errors_are_raised():
    execute = _execute_returning(_command_error("slurm_load_jobs error: Unable to contact slurm controller\n"))
    with pytest.raises(commands.CommandLineException):
        slurm_job_state("7", execute=execute)


@pytest.mark.parametrize(
    "stderr,expected,message",
    [
        (b"tool noise\nslurmstepd: error: Exceeded job memory limit\n", MEMORY_LIMIT_EXCEEDED, OUT_OF_MEMORY_MSG),
        (
            b"slurmstepd: error: task/cgroup: Exceeded job memory limit at some point.\n",
            MEMORY_LIMIT_PROBABLY_EXCEEDED,
            PROBABLY_OUT_OF_MEMORY_MSG,
        ),
        (
            b"slurmstepd: error: task/cgroup: Exceeded step memory limit at some point.\n",
            MEMORY_LIMIT_PROBABLY_EXCEEDED,
            PROBABLY_OUT_OF_MEMORY_MSG,
        ),
    ],
)
def test_memory_limit_messages(tmp_path, stderr, expected, message):
    efile = tmp_path / "stderr"
    efile.write_bytes(stderr)
    assert check_memory_limit(str(efile)) == expected
    assert MEMORY_LIMIT_MESSAGES[expected] == message


def test_no_memory_limit_message(tmp_path):
    efile = tmp_path / "stderr"
    efile.write_bytes(b"tool noise\n")
    assert check_memory_limit(str(efile)) is None


def test_only_end_of_file_is_searched(tmp_path):
    efile = tmp_path / "stderr"
    efile.write_bytes(b"slurmstepd: error: Exceeded job memory limit\n" + b"x\n" * 2048)
    assert check_memory_limit(str(efile)) is None


def test_missing_stderr_file_is_not_an_error(tmp_path):
    assert check_memory_limit(str(tmp_path / "missing")) is None
