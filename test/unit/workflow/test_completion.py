"""Unit tests for workflow completion detection logic."""

from typing import cast

from galaxy import model
from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.managers.workflow_completion import WorkflowCompletionManager
from galaxy.schema.invocation import (
    InvocationState,
    InvocationStepState,
)
from galaxy.schema.schema import JobState
from galaxy.structured_app import MinimalManagerApp


class TestWorkflowInvocationStepIsComplete:
    """Tests for WorkflowInvocationStep.is_complete model property."""

    def test_step_without_jobs_in_scheduled_state_is_complete(self):
        """Input/parameter steps without jobs are complete when scheduled."""
        step = model.WorkflowInvocationStep()
        workflow_step = model.WorkflowStep()
        workflow_step.type = "data_input"
        step.workflow_step = workflow_step
        step.state = InvocationStepState.SCHEDULED

        assert step.is_complete is True

    def test_step_without_jobs_in_new_state_is_not_complete(self):
        """Input steps in NEW state are not complete."""
        step = model.WorkflowInvocationStep()
        workflow_step = model.WorkflowStep()
        workflow_step.type = "data_input"
        step.workflow_step = workflow_step
        step.state = InvocationStepState.NEW

        assert step.is_complete is False

    def test_step_with_all_ok_jobs_is_complete(self):
        """Tool step with all OK jobs is complete."""
        job = model.Job()
        job.state = JobState.OK

        step = model.WorkflowInvocationStep()
        workflow_step = model.WorkflowStep()
        workflow_step.type = "tool"
        step.workflow_step = workflow_step
        step.job = job

        assert step.is_complete is True

    def test_step_with_running_job_is_not_complete(self):
        """Tool step with a running job is not complete."""
        job = model.Job()
        job.state = JobState.RUNNING

        step = model.WorkflowInvocationStep()
        workflow_step = model.WorkflowStep()
        workflow_step.type = "tool"
        step.workflow_step = workflow_step
        step.job = job

        assert step.is_complete is False

    def test_step_with_error_job_is_complete(self):
        """Tool step with error job is still complete (error is terminal)."""
        job = model.Job()
        job.state = JobState.ERROR

        step = model.WorkflowInvocationStep()
        workflow_step = model.WorkflowStep()
        workflow_step.type = "tool"
        step.workflow_step = workflow_step
        step.job = job

        assert step.is_complete is True


class TestWorkflowInvocationIsComplete:
    """Tests for WorkflowInvocation.is_complete model property."""

    def test_invocation_not_in_scheduled_state_is_not_complete(self):
        """Invocations not in SCHEDULED state are not complete."""
        invocation = model.WorkflowInvocation()
        invocation.state = InvocationState.NEW

        assert invocation.is_complete is False

    def test_scheduled_invocation_with_all_complete_steps_is_complete(self):
        """Scheduled invocation with all steps complete is complete."""
        job = model.Job()
        job.state = JobState.OK

        workflow_step = model.WorkflowStep()
        workflow_step.type = "tool"

        step = model.WorkflowInvocationStep()
        step.workflow_step = workflow_step
        step.job = job

        invocation = model.WorkflowInvocation()
        invocation.state = InvocationState.SCHEDULED
        invocation.steps.append(step)

        assert invocation.is_complete is True

    def test_scheduled_invocation_with_incomplete_step_is_not_complete(self):
        """Scheduled invocation with running job is not complete."""
        job = model.Job()
        job.state = JobState.RUNNING

        workflow_step = model.WorkflowStep()
        workflow_step.type = "tool"

        step = model.WorkflowInvocationStep()
        step.workflow_step = workflow_step
        step.job = job

        invocation = model.WorkflowInvocation()
        invocation.state = InvocationState.SCHEDULED
        invocation.steps.append(step)

        assert invocation.is_complete is False


class TestComputeRecursiveJobStateSummary:
    """Tests for WorkflowInvocation.compute_recursive_job_state_summary method."""

    def test_empty_invocation_returns_empty_dict(self):
        """Invocation with no jobs returns empty summary."""
        workflow_step = model.WorkflowStep()
        workflow_step.type = "data_input"

        step = model.WorkflowInvocationStep()
        step.workflow_step = workflow_step

        invocation = model.WorkflowInvocation()
        invocation.state = InvocationState.SCHEDULED
        invocation.steps.append(step)

        summary = invocation.compute_recursive_job_state_summary()
        assert summary == {}

    def test_counts_job_states_correctly(self):
        """Job states are counted correctly."""
        job1 = model.Job()
        job1.state = JobState.OK.value
        job2 = model.Job()
        job2.state = JobState.OK.value
        job3 = model.Job()
        job3.state = JobState.ERROR.value

        workflow_step1 = model.WorkflowStep()
        workflow_step1.type = "tool"
        workflow_step2 = model.WorkflowStep()
        workflow_step2.type = "tool"
        workflow_step3 = model.WorkflowStep()
        workflow_step3.type = "tool"

        step1 = model.WorkflowInvocationStep()
        step1.workflow_step = workflow_step1
        step1.job = job1

        step2 = model.WorkflowInvocationStep()
        step2.workflow_step = workflow_step2
        step2.job = job2

        step3 = model.WorkflowInvocationStep()
        step3.workflow_step = workflow_step3
        step3.job = job3

        invocation = model.WorkflowInvocation()
        invocation.state = InvocationState.SCHEDULED
        invocation.steps.append(step1)
        invocation.steps.append(step2)
        invocation.steps.append(step3)

        summary = invocation.compute_recursive_job_state_summary()
        assert summary == {"ok": 2, "error": 1}


class TestWorkflowCompletionManagerHandlerFiltering:
    """Tests for WorkflowCompletionManager.poll_pending_completions handler filtering."""

    def test_poll_pending_completions_filters_by_handler(self):
        """poll_pending_completions should only return invocations for the specified handler."""
        app = MockApp()
        session = app.model.context

        # Create a user and workflow (required for invocations)
        user = model.User(email="test@test.com", password="password")
        session.add(user)

        stored_workflow = model.StoredWorkflow()
        stored_workflow.user = user
        workflow = model.Workflow()
        stored_workflow.latest_workflow = workflow
        workflow.stored_workflow = stored_workflow
        session.add(stored_workflow)
        session.flush()

        # Create invocations with different handlers and SCHEDULED state
        inv1 = model.WorkflowInvocation()
        inv1.workflow = workflow
        inv1.state = InvocationState.SCHEDULED.value
        inv1.handler = "handler_a"

        inv2 = model.WorkflowInvocation()
        inv2.workflow = workflow
        inv2.state = InvocationState.SCHEDULED.value
        inv2.handler = "handler_a"

        inv3 = model.WorkflowInvocation()
        inv3.workflow = workflow
        inv3.state = InvocationState.SCHEDULED.value
        inv3.handler = "handler_b"

        session.add_all([inv1, inv2, inv3])
        session.commit()

        # Create the completion manager and test filtering
        completion_manager = WorkflowCompletionManager(cast(MinimalManagerApp, app))

        # Poll with handler_a - should return 2 invocations
        handler_a_pending = completion_manager.poll_pending_completions(handler="handler_a")
        assert len(handler_a_pending) == 2
        assert inv1.id in handler_a_pending
        assert inv2.id in handler_a_pending
        assert inv3.id not in handler_a_pending

        # Poll with handler_b - should return only 1 invocation
        handler_b_pending = completion_manager.poll_pending_completions(handler="handler_b")
        assert len(handler_b_pending) == 1
        assert inv3.id in handler_b_pending

        # Poll with a non-existent handler - should return empty
        other_pending = completion_manager.poll_pending_completions(handler="nonexistent_handler")
        assert len(other_pending) == 0

        # Poll without handler filtering - should return all 3
        all_pending = completion_manager.poll_pending_completions(handler=None)
        assert len(all_pending) == 3

    def test_poll_pending_completions_excludes_non_scheduled_invocations(self):
        """poll_pending_completions should only return SCHEDULED invocations."""
        app = MockApp()
        session = app.model.context

        user = model.User(email="test2@test.com", password="password")
        session.add(user)

        stored_workflow = model.StoredWorkflow()
        stored_workflow.user = user
        workflow = model.Workflow()
        stored_workflow.latest_workflow = workflow
        workflow.stored_workflow = stored_workflow
        session.add(stored_workflow)
        session.flush()

        # Create invocations with different states, same handler
        inv_scheduled = model.WorkflowInvocation()
        inv_scheduled.workflow = workflow
        inv_scheduled.state = InvocationState.SCHEDULED.value
        inv_scheduled.handler = "handler_a"

        inv_new = model.WorkflowInvocation()
        inv_new.workflow = workflow
        inv_new.state = InvocationState.NEW.value
        inv_new.handler = "handler_a"

        inv_ready = model.WorkflowInvocation()
        inv_ready.workflow = workflow
        inv_ready.state = InvocationState.READY.value
        inv_ready.handler = "handler_a"

        session.add_all([inv_scheduled, inv_new, inv_ready])
        session.commit()

        completion_manager = WorkflowCompletionManager(cast(MinimalManagerApp, app))

        # Only the SCHEDULED invocation should be returned
        pending = completion_manager.poll_pending_completions(handler="handler_a")
        assert len(pending) == 1
        assert inv_scheduled.id in pending
