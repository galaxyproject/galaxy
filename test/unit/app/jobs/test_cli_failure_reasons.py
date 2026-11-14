from types import SimpleNamespace
from unittest.mock import MagicMock

from galaxy.jobs.runners.cli import ShellJobRunner
from galaxy.jobs.runners.runner_state_definitions import RUNNER_STATE_DEFINITIONS
from galaxy.jobs.runners.util import runner_states
from galaxy.jobs.runners.util.cli.job.slurm import Slurm


def _handle(stdout):
    shell = MagicMock()
    shell.execute.return_value = SimpleNamespace(stdout=stdout)
    runner = MagicMock()
    runner.parse_destination_params.return_value = ({}, {})
    runner.get_cli_plugins.return_value = (shell, Slurm())
    ajs = MagicMock(runner_state=None, fail_message=None)
    ShellJobRunner._handle_job_failure_reasons(runner, ajs, "12")
    return ajs


def test_registered_reason_sets_state_and_message():
    ajs = _handle("JobId=12 JobState=NODE_FAIL Reason=NodeDown\n")
    assert ajs.runner_state == runner_states.NODE_FAILURE
    assert ajs.fail_message == RUNNER_STATE_DEFINITIONS[runner_states.NODE_FAILURE].fail_message


def test_plugin_details_are_used_without_a_reason():
    ajs = _handle("JobId=12 JobState=FAILED Reason=RaisedSignal:9(Killed)\n")
    assert ajs.runner_state is None
    assert ajs.fail_message == "Slurm reported: RaisedSignal:9(Killed)"


def test_nothing_is_set_for_an_ordinary_failure():
    ajs = _handle("JobId=12 JobState=FAILED Reason=NonZeroExitCode\n")
    assert ajs.runner_state is None
    assert ajs.fail_message is None
