import pytest

from galaxy.jobs.runners.cli import failure_reason_from_output
from galaxy.jobs.runners.runner_state_definitions import RUNNER_STATE_DEFINITIONS
from galaxy.jobs.runners.util import runner_states
from galaxy.jobs.runners.util.cli.job.slurm import Slurm


def _reason(stdout):
    return failure_reason_from_output(Slurm(), stdout, "12")


@pytest.mark.parametrize(
    "stdout,runner_state",
    [
        ("JobId=12 JobState=NODE_FAIL Reason=NodeDown\n", runner_states.NODE_FAILURE),
        ("JobId=12 JobState=PREEMPTED Reason=None\n", runner_states.PREEMPTED),
        ("JobId=12 JobState=OUT_OF_MEMORY Reason=OutOfMemory\n", runner_states.MEMORY_LIMIT_REACHED),
        # scontrol has forgotten the job, sacct still knows it.
        ("12|CANCELLED by 1000\n12.batch|CANCELLED\n", runner_states.CANCELLED),
        ("12|TIMEOUT\n12.batch|CANCELLED\n12.extern|COMPLETED\n", runner_states.WALLTIME_REACHED),
    ],
)
def test_registered_reason_sets_state_and_message(stdout, runner_state):
    assert _reason(stdout) == (runner_state, RUNNER_STATE_DEFINITIONS[runner_state].fail_message)


def test_plugin_details_are_used_without_a_reason():
    assert _reason("JobId=12 JobState=FAILED Reason=RaisedSignal:9(Killed)\n") == (
        None,
        "Slurm reported: RaisedSignal:9(Killed)",
    )


def test_nothing_is_set_for_an_ordinary_failure():
    assert _reason("JobId=12 JobState=FAILED Reason=NonZeroExitCode\n") == (None, None)
