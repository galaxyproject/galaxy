import logging
from types import SimpleNamespace

import pytest

from galaxy.jobs.runners.util.cli.job import job_states
from galaxy.jobs.runners.util.cli.job.slurm import Slurm

SQUEUE_HEADER = "JOBID ST\n"


class FakeShell:
    """Answers the ``sacct`` fallback with canned output."""

    def __init__(self, stdout="", stderr=""):
        self.result = SimpleNamespace(stdout=stdout, stderr=stderr)
        self.commands = []

    def execute(self, command):
        self.commands.append(command)
        return self.result


def _single_status(squeue_stdout, shell=None):
    return Slurm().parse_single_status(squeue_stdout, "12", shell or FakeShell())


@pytest.mark.parametrize(
    "code,expected",
    [
        ("PR", job_states.ERROR),
        ("F", job_states.ERROR),
        ("CD", job_states.OK),
        ("R", job_states.RUNNING),
        ("CF", job_states.QUEUED),
    ],
)
def test_squeue_state_of_a_listed_job(code, expected):
    shell = FakeShell()
    assert _single_status(f"{SQUEUE_HEADER}12 {code}\n", shell) == expected
    assert shell.commands == []


@pytest.mark.parametrize(
    "sacct_stdout,expected",
    [
        ("12|CANCELLED by 1000\n12.batch|CANCELLED\n", job_states.ERROR),
        ("12|PREEMPTED\n12.batch|CANCELLED\n12.extern|COMPLETED\n", job_states.ERROR),
        ("12|COMPLETED\n12.batch|COMPLETED\n", job_states.OK),
        ("", job_states.ERROR),
    ],
)
def test_sacct_state_of_a_job_squeue_no_longer_lists(sacct_stdout, expected):
    shell = FakeShell(stdout=sacct_stdout)
    assert _single_status(SQUEUE_HEADER, shell) == expected
    assert shell.commands == ["sacct -o JobIDRaw,State -P -n -j 12"]


def test_job_without_accounting_is_assumed_finished():
    slurm = Slurm()
    shell = FakeShell(stderr="Slurm accounting storage is disabled")
    assert slurm.parse_single_status(SQUEUE_HEADER, "12", shell) == job_states.OK
    assert slurm.sacct_available is False


def test_unknown_state_code_is_logged_and_kept_watching(caplog):
    with caplog.at_level(logging.WARNING):
        assert _single_status(f"{SQUEUE_HEADER}12 XX\n") == job_states.RUNNING
    assert "Unknown Slurm job state code [XX]" in caplog.text


def test_bulk_status_maps_listed_jobs():
    status = f"{SQUEUE_HEADER}12 R\n13 PD\n14 CG\n99 R\n"
    assert Slurm().parse_status(status, ["12", "13", "14"]) == {
        "12": job_states.RUNNING,
        "13": job_states.QUEUED,
        "14": job_states.RUNNING,
    }
