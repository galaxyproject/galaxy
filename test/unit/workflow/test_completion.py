"""Unit tests for workflow completion detection logic."""

from unittest.mock import (
    MagicMock,
)

import pytest

from galaxy.schema.invocation import (
    InvocationState,
    InvocationStepState,
)
from galaxy.schema.schema import JobState
from galaxy.workflow.completion import (
    are_all_jobs_successful,
    compute_job_state_summary,
    is_invocation_complete,
    is_job_terminal,
    is_step_complete,
    SUCCESSFUL_JOB_STATES,
    TERMINAL_JOB_STATES,
)


class TestIsJobTerminal:
    """Tests for is_job_terminal function."""

    @pytest.mark.parametrize(
        "state",
        [
            JobState.OK.value,
            JobState.ERROR.value,
            JobState.DELETED.value,
            JobState.SKIPPED.value,
            JobState.PAUSED.value,
            JobState.STOPPED.value,
        ],
    )
    def test_terminal_states_return_true(self, state):
        """All terminal states should return True."""
        job = MagicMock()
        job.state = state
        assert is_job_terminal(job) is True

    @pytest.mark.parametrize(
        "state",
        [
            JobState.NEW.value,
            JobState.QUEUED.value,
            JobState.RUNNING.value,
            JobState.WAITING.value,
            JobState.UPLOAD.value,
        ],
    )
    def test_non_terminal_states_return_false(self, state):
        """Non-terminal states should return False."""
        job = MagicMock()
        job.state = state
        assert is_job_terminal(job) is False


class TestIsStepComplete:
    """Tests for is_step_complete function."""

    def test_step_without_jobs_in_scheduled_state_is_complete(self):
        """Input/parameter steps without jobs are complete when scheduled."""
        step = MagicMock()
        step.workflow_step.type = "data_input"
        step.jobs = []
        step.state = InvocationStepState.SCHEDULED.value

        assert is_step_complete(step) is True

    def test_step_without_jobs_in_new_state_is_not_complete(self):
        """Input steps in NEW state are not complete."""
        step = MagicMock()
        step.workflow_step.type = "data_input"
        step.jobs = []
        step.state = InvocationStepState.NEW.value

        assert is_step_complete(step) is False

    def test_step_with_all_ok_jobs_is_complete(self):
        """Tool step with all OK jobs is complete."""
        job1 = MagicMock()
        job1.state = JobState.OK.value
        job2 = MagicMock()
        job2.state = JobState.OK.value

        step = MagicMock()
        step.workflow_step.type = "tool"
        step.jobs = [job1, job2]

        assert is_step_complete(step) is True

    def test_step_with_running_job_is_not_complete(self):
        """Tool step with a running job is not complete."""
        job1 = MagicMock()
        job1.state = JobState.OK.value
        job2 = MagicMock()
        job2.state = JobState.RUNNING.value

        step = MagicMock()
        step.workflow_step.type = "tool"
        step.jobs = [job1, job2]

        assert is_step_complete(step) is False

    def test_step_with_error_job_is_complete(self):
        """Tool step with error job is still complete (error is terminal)."""
        job = MagicMock()
        job.state = JobState.ERROR.value

        step = MagicMock()
        step.workflow_step.type = "tool"
        step.jobs = [job]

        assert is_step_complete(step) is True


class TestIsInvocationComplete:
    """Tests for is_invocation_complete function."""

    def test_invocation_not_in_scheduled_state_is_not_complete(self):
        """Invocations not in SCHEDULED state are not complete."""
        invocation = MagicMock()
        invocation.state = InvocationState.NEW.value
        invocation.steps = []

        assert is_invocation_complete(invocation) is False

    def test_scheduled_invocation_with_all_complete_steps_is_complete(self):
        """Scheduled invocation with all steps complete is complete."""
        job = MagicMock()
        job.state = JobState.OK.value

        step = MagicMock()
        step.workflow_step.type = "tool"
        step.jobs = [job]

        invocation = MagicMock()
        invocation.state = InvocationState.SCHEDULED.value
        invocation.steps = [step]

        assert is_invocation_complete(invocation) is True

    def test_scheduled_invocation_with_incomplete_step_is_not_complete(self):
        """Scheduled invocation with running job is not complete."""
        job = MagicMock()
        job.state = JobState.RUNNING.value

        step = MagicMock()
        step.workflow_step.type = "tool"
        step.jobs = [job]

        invocation = MagicMock()
        invocation.state = InvocationState.SCHEDULED.value
        invocation.steps = [step]

        assert is_invocation_complete(invocation) is False


class TestComputeJobStateSummary:
    """Tests for compute_job_state_summary function."""

    def test_empty_invocation_returns_empty_dict(self):
        """Invocation with no jobs returns empty summary."""
        step = MagicMock()
        step.workflow_step.type = "data_input"
        step.jobs = []

        invocation = MagicMock()
        invocation.steps = [step]

        summary = compute_job_state_summary(invocation)
        assert summary == {}

    def test_counts_job_states_correctly(self):
        """Job states are counted correctly."""
        job1 = MagicMock()
        job1.state = JobState.OK.value
        job2 = MagicMock()
        job2.state = JobState.OK.value
        job3 = MagicMock()
        job3.state = JobState.ERROR.value

        step1 = MagicMock()
        step1.workflow_step.type = "tool"
        step1.jobs = [job1, job2]

        step2 = MagicMock()
        step2.workflow_step.type = "tool"
        step2.jobs = [job3]

        invocation = MagicMock()
        invocation.steps = [step1, step2]

        summary = compute_job_state_summary(invocation)
        assert summary == {"ok": 2, "error": 1}


class TestAreAllJobsSuccessful:
    """Tests for are_all_jobs_successful function."""

    def test_all_ok_jobs_is_successful(self):
        """Summary with only OK jobs is successful."""
        assert are_all_jobs_successful({"ok": 5}) is True

    def test_ok_and_skipped_is_successful(self):
        """Summary with OK and SKIPPED jobs is successful."""
        assert are_all_jobs_successful({"ok": 3, "skipped": 2}) is True

    def test_error_jobs_is_not_successful(self):
        """Summary with error jobs is not successful."""
        assert are_all_jobs_successful({"ok": 3, "error": 1}) is False

    def test_empty_summary_is_successful(self):
        """Empty summary (no jobs) is considered successful."""
        assert are_all_jobs_successful({}) is True


class TestTerminalStates:
    """Tests for terminal state constants."""

    def test_terminal_states_are_strings(self):
        """Terminal states should be string values."""
        for state in TERMINAL_JOB_STATES:
            assert isinstance(state, str)

    def test_successful_states_subset_of_terminal(self):
        """Successful states should be a subset of terminal states."""
        assert SUCCESSFUL_JOB_STATES.issubset(TERMINAL_JOB_STATES)
