"""Unit tests for workflow completion detection logic."""

from typing import cast

import pytest
from sqlalchemy import event

from galaxy import model
from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.managers.workflow_completion import WorkflowCompletionManager
from galaxy.schema.states import (
    InvocationState,
    InvocationStepState,
    JobState,
)
from galaxy.structured_app import MinimalManagerApp
from galaxy.workflow.completion_hooks import WorkflowCompletionHookRegistry
from galaxy.workflow.completion_monitor import WorkflowCompletionMonitor


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


class TestNestedWorkflowCompletion:
    @pytest.fixture
    def completion_tree(self):
        app = MockApp()
        session = app.model.context
        invocations = []
        for _ in range(3):
            workflow = model.Workflow()
            invocation = model.WorkflowInvocation()
            invocation.workflow = workflow
            invocation.state = InvocationState.SCHEDULED.value
            invocation.handler = "handler_a"
            session.add(invocation)
            invocations.append(invocation)

        for parent, child in zip(invocations, invocations[1:]):
            workflow_step = model.WorkflowStep()
            workflow_step.order_index = 0
            workflow_step.type = "subworkflow"
            workflow_step.subworkflow = child.workflow
            parent.workflow.steps.append(workflow_step)

            step = model.WorkflowInvocationStep()
            step.workflow_step = workflow_step
            step.state = InvocationStepState.SCHEDULED.value
            parent.steps.append(step)

            association = model.WorkflowInvocationToSubworkflowInvocationAssociation()
            association.workflow_step = workflow_step
            association.subworkflow_invocation = child
            parent.subworkflow_invocations.append(association)

        workflow_step = model.WorkflowStep()
        workflow_step.type = "tool"
        invocations[-1].workflow.steps.append(workflow_step)
        workflow_step.order_index = 0
        step = model.WorkflowInvocationStep()
        step.workflow_step = workflow_step
        step.job = model.Job()
        step.job.state = JobState.OK.value
        invocations[-1].steps.append(step)
        session.commit()
        return WorkflowCompletionManager(cast(MinimalManagerApp, app)), invocations

    def test_parent_waits_for_recorded_subworkflow_completion(self, completion_tree):
        manager, invocations = completion_tree
        for parent in invocations[:-1]:
            assert manager.check_and_record_completion(parent.id) is None
            assert parent.state == InvocationState.SCHEDULED.value
            assert manager.get_completion(parent.id) is None

        for invocation in reversed(invocations):
            completion = manager.check_and_record_completion(invocation.id)
            assert completion is not None
            assert invocation.state == InvocationState.COMPLETED.value
            assert completion.job_state_summary == {"ok": 1}

    def test_waiting_parents_do_not_fill_completion_batch(self, completion_tree):
        manager, invocations = completion_tree
        for invocation in reversed(invocations):
            assert manager.poll_pending_completions(limit=1, handler="handler_a") == [invocation.id]
            assert manager.check_and_record_completion(invocation.id) is not None

        assert manager.poll_pending_completions(limit=1, handler="handler_a") == []

    def test_parent_completes_after_rescheduling_completed_subworkflow(self, completion_tree):
        manager, invocations = completion_tree
        child = invocations[-1]
        assert manager.check_and_record_completion(child.id) is not None

        # Scheduling the parent's subworkflow step runs the child's invoker again.
        child.set_state(InvocationState.SCHEDULED)
        manager.sa_session.commit()

        assert child.state == InvocationState.COMPLETED.value
        for invocation in reversed(invocations[:-1]):
            assert manager.poll_pending_completions(limit=1, handler="handler_a") == [invocation.id]
            assert manager.check_and_record_completion(invocation.id) is not None


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


class TestMappedWorkflowCompletion:
    @pytest.fixture
    def mapped_invocation(self):
        app = MockApp()
        session = app.model.context
        workflow = model.Workflow()
        workflow_step = model.WorkflowStep()
        workflow_step.type = "tool"
        workflow_step.order_index = 0
        workflow.steps.append(workflow_step)
        invocation = model.WorkflowInvocation()
        invocation.workflow = workflow
        invocation.state = InvocationState.SCHEDULED.value
        step = model.WorkflowInvocationStep()
        step.workflow_step = workflow_step
        step.state = InvocationStepState.SCHEDULED.value
        step.implicit_collection_jobs = model.ImplicitCollectionJobs(populated_state="ok")
        invocation.steps.append(step)
        session.add(invocation)
        session.commit()
        return app, invocation

    @pytest.mark.parametrize("size", [1, 1000])
    def test_completion_and_summary_do_not_load_mapped_jobs(self, mapped_invocation, size):
        app, invocation = mapped_invocation
        session = app.model.context
        for index in range(size):
            association = model.ImplicitCollectionJobsJobAssociation()
            association.order_index = index
            association.job = model.Job()
            association.job.state = JobState.OK.value if index else JobState.ERROR.value
            invocation.steps[0].implicit_collection_jobs.jobs.append(association)
        session.commit()
        invocation_id = invocation.id
        session.expunge_all()

        def reject_job_load(session, instance):
            assert not isinstance(instance, model.Job), "Completion polling must not materialize mapped jobs"

        event.listen(session(), "loaded_as_persistent", reject_job_load)
        try:
            manager = WorkflowCompletionManager(cast(MinimalManagerApp, app))
            completion = manager.check_and_record_completion(invocation_id)
            assert completion is not None
            expected = {"error": 1}
            if size > 1:
                expected["ok"] = size - 1
            assert completion.job_state_summary == expected
            assert manager.check_and_record_completion(invocation_id) is None
        finally:
            event.remove(session(), "loaded_as_persistent", reject_job_load)

    @pytest.mark.parametrize("state", [JobState.RUNNING, JobState.DELETING, JobState.PAUSED, JobState.SKIPPED])
    def test_waits_for_unsettled_jobs(self, mapped_invocation, state):
        app, invocation = mapped_invocation
        association = model.ImplicitCollectionJobsJobAssociation()
        association.order_index = 0
        association.job = model.Job()
        association.job.state = state.value
        invocation.steps[0].implicit_collection_jobs.jobs.append(association)
        app.model.context.commit()
        assert invocation.is_complete is (state in (JobState.PAUSED, JobState.SKIPPED))

    def test_cached_jobs_do_not_complete_until_map_is_populated(self, mapped_invocation):
        app, invocation = mapped_invocation
        collection_jobs = invocation.steps[0].implicit_collection_jobs
        collection_jobs.populated_state = "new"
        association = model.ImplicitCollectionJobsJobAssociation()
        association.order_index = 0
        association.job = model.Job()
        association.job.state = JobState.OK.value
        collection_jobs.jobs.append(association)
        app.model.context.commit()
        assert not invocation.is_complete
        collection_jobs.populated_state = "ok"
        app.model.context.commit()
        assert invocation.is_complete

    def test_monitor_reaches_completions_beyond_a_full_batch_of_running_invocations(self, mapped_invocation):
        app, invocation = mapped_invocation
        session = app.model.context
        workflow = invocation.workflow
        invocation.handler = "handler_a"
        # This invocation and the next 99 remain unfinished.
        invocation.steps[0].implicit_collection_jobs.populated_state = "new"
        for _ in range(99):
            waiting = model.WorkflowInvocation()
            waiting.workflow = workflow
            waiting.handler = "handler_a"
            waiting.state = InvocationState.SCHEDULED.value
            step = model.WorkflowInvocationStep()
            step.workflow_step = workflow.steps[0]
            step.state = InvocationStepState.NEW.value
            waiting.steps.append(step)
            session.add(waiting)
        ready = model.WorkflowInvocation()
        ready.workflow = workflow
        ready.handler = "handler_a"
        ready.state = InvocationState.SCHEDULED.value
        session.add(ready)
        session.commit()
        first_id, ready_id = invocation.id, ready.id
        app.config.server_name = "handler_a"
        app.config.workflow_completion_monitor_sleep = 5
        manager = WorkflowCompletionManager(cast(MinimalManagerApp, app))
        registry = WorkflowCompletionHookRegistry(cast(MinimalManagerApp, app))
        monitor = WorkflowCompletionMonitor(cast(MinimalManagerApp, app), manager, registry)

        monitor._monitor_step()
        assert manager.get_completion(ready_id) is None
        monitor._monitor_step()
        assert manager.get_completion(ready_id) is not None

        # Reach the end, wrap, and pick up a previously unfinished invocation.
        monitor._monitor_step()
        first = session.get(model.WorkflowInvocation, first_id)
        first.steps[0].implicit_collection_jobs.populated_state = "ok"
        session.commit()
        monitor._monitor_step()
        assert manager.get_completion(first_id) is not None
