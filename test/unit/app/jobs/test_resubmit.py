from unittest.mock import MagicMock

import pytest

from galaxy.jobs.runners import JobState
from galaxy.jobs.runners.state_handlers.resubmit import (
    _ExpressionContext,
    failure,
)
from galaxy.jobs.runners.util import (
    register_runner_state,
    RUNNER_STATE_DEFINITIONS,
    runner_states,
)

HANDLED_RUNNER_STATES = [
    (JobState.runner_states.WALLTIME_REACHED, "walltime_reached"),
    (JobState.runner_states.MEMORY_LIMIT_REACHED, "memory_limit_reached"),
    (JobState.runner_states.JOB_OUTPUT_NOT_RETURNED_FROM_CLUSTER, "job_output_not_returned_from_cluster"),
    (JobState.runner_states.TOOL_DETECT_ERROR, "tool_detected_failure"),
    (JobState.runner_states.TOOL_TIMELIMIT_REACHED, "tool_timelimit_reached"),
    (JobState.runner_states.UNKNOWN_ERROR, "unknown_error"),
    (JobState.runner_states.NODE_FAILURE, "node_failure"),
    (JobState.runner_states.PREEMPTED, "preempted"),
]


def _job_state(runner_state, resubmit):
    job_state = MagicMock(runner_state=runner_state)
    job_state.runner_state_handled = False
    job_state.job_destination.resubmit = resubmit
    job = job_state.job_wrapper.get_job.return_value
    job.resubmission_count = 0
    job.state_history = []
    job.destination_params = {}
    return job_state


@pytest.mark.parametrize("runner_state,condition", HANDLED_RUNNER_STATES)
def test_every_handled_runner_state_has_a_message(runner_state, condition):
    assert RUNNER_STATE_DEFINITIONS[runner_state].resubmit_description


@pytest.mark.parametrize("runner_state,condition", HANDLED_RUNNER_STATES)
def test_every_handled_runner_state_has_a_condition(runner_state, condition):
    context = _ExpressionContext(_job_state(runner_state, []))
    assert context.safe_eval(condition) is True
    other_conditions = [other for _, other in HANDLED_RUNNER_STATES if other != condition]
    assert not any(context.safe_eval(other) for other in other_conditions)


@pytest.mark.parametrize("runner_state,condition", HANDLED_RUNNER_STATES)
def test_resubmits_for_every_handled_runner_state(runner_state, condition):
    job_state = _job_state(runner_state, [{"condition": condition}])
    failure(MagicMock(), MagicMock(), job_state)
    assert job_state.runner_state_handled is True


def test_does_not_resubmit_when_condition_is_for_another_state():
    job_state = _job_state(JobState.runner_states.WALLTIME_REACHED, [{"condition": "memory_limit_reached"}])
    failure(MagicMock(), MagicMock(), job_state)
    assert job_state.runner_state_handled is False


@pytest.mark.parametrize(
    "runner_state",
    [
        JobState.runner_states.CANCELLED,
        JobState.runner_states.GLOBAL_WALLTIME_REACHED,
        JobState.runner_states.OUTPUT_SIZE_LIMIT,
    ],
)
def test_states_without_a_description_are_never_resubmitted(runner_state):
    job_state = _job_state(runner_state, [{"condition": "any_failure"}])
    failure(MagicMock(), MagicMock(), job_state)
    assert job_state.runner_state_handled is False


@pytest.fixture
def registered_reason():
    value = register_runner_state(
        "TEST_GPU_LOST", "test_gpu_lost", resubmit_description="its GPU was lost", condition="test_gpu_lost"
    )
    yield value
    del RUNNER_STATE_DEFINITIONS[value]
    del runner_states.__dict__["TEST_GPU_LOST"]


def test_registering_a_reason_makes_it_available_to_conditions(registered_reason):
    job_state = _job_state(registered_reason, [{"condition": "test_gpu_lost"}])
    failure(MagicMock(), MagicMock(), job_state)
    assert job_state.runner_state_handled is True


def test_registered_reason_does_not_count_as_unknown(registered_reason):
    context = _ExpressionContext(_job_state(registered_reason, []))
    assert context.safe_eval("unknown_error") is False


def test_reason_without_definition_counts_as_unknown():
    context = _ExpressionContext(_job_state("from_the_future", []))
    assert context.safe_eval("unknown_error") is True
    assert context.safe_eval("memory_limit_reached") is False


def test_reason_without_definition_can_be_matched_by_name():
    job_state = _job_state("from_the_future", [{"condition": "runner_state == 'from_the_future'"}])
    failure(MagicMock(), MagicMock(), job_state)
    assert job_state.runner_state_handled is True
