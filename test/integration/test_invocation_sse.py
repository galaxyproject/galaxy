"""Integration tests for ``invocation_update`` SSE events on workflow invocation changes.

The populator waits re-check invocations only when an ``invocation_update`` event for them
arrives once the server has SSE updates enabled, so every wait here also asserts that the
event was sent.
"""

import json
from uuid import uuid4

from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.base.sse import (
    DEFAULT_WAIT_TIMEOUT,
    invocation_states_for,
    job_states_for,
)
from galaxy_test.base.workflow_fixtures import WORKFLOW_NESTED_SIMPLE
from galaxy_test.driver.integration_util import SSEIntegrationTestCase

WORKFLOW_WITH_PAUSE = """
class: GalaxyWorkflow
inputs:
  test_input: data
steps:
  the_pause:
    type: pause
    in:
      input: test_input
  cat_after_pause:
    tool_id: cat1
    in:
      input1: the_pause
"""

WORKFLOW_ONE_STEP = """
class: GalaxyWorkflow
inputs:
  test_input: data
steps:
  cat:
    tool_id: cat1
    in:
      input1: test_input
"""

WORKFLOW_THREE_INDEPENDENT_STEPS = """
class: GalaxyWorkflow
inputs:
  test_input: data
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: test_input
  second_cat:
    tool_id: cat1
    in:
      input1: test_input
  third_cat:
    tool_id: cat1
    in:
      input1: test_input
"""


class BaseInvocationSSEIntegrationTestCase(SSEIntegrationTestCase):
    def _invocation_state(self, invocation_id: str) -> str:
        return self.workflow_populator.get_invocation(invocation_id)["state"]

    def _new_user_api_key(self) -> str:
        user = self._setup_user(f"{uuid4()}@galaxy.test")
        _, api_key = self._setup_user_get_key(user["email"])
        return api_key

    def _subscribe_as_viewer(self, api_key: str, history_id: str) -> None:
        DatasetPopulator(self._get_interactor(api_key=api_key)).subscribe_history_viewer([history_id])


class TestInvocationSSEIntegration(BaseInvocationSSEIntegrationTestCase):
    def test_owner_receives_lifecycle_of_invocation_and_subworkflow(self):
        other_user = self._setup_user(f"{uuid4()}@galaxy.test")
        _, other_api_key = self._setup_user_get_key(other_user["email"])

        owner_listener = self._listener()
        other_listener = self._listener(other_api_key)
        try:
            with self.dataset_populator.test_history() as history_id:
                summary = self.workflow_populator.run_workflow(
                    WORKFLOW_NESTED_SIMPLE,
                    test_data={"outer_input": {"value": "1.bed", "type": "File"}},
                    history_id=history_id,
                    wait=False,
                )
                invocation_id = summary.invocation_id
                self.workflow_populator.wait_for_invocation_and_completion(invocation_id)
                invocation = self.workflow_populator.get_invocation(invocation_id)
                (subworkflow_invocation_id,) = (
                    step["subworkflow_invocation_id"]
                    for step in invocation["steps"]
                    if step["subworkflow_invocation_id"]
                )
                self.workflow_populator.wait_for_invocation_and_completion(subworkflow_invocation_id)
                # The waits can see committed states before their events reach this listener.
                for completed_id in (invocation_id, subworkflow_invocation_id):
                    owner_listener.wait_for_event_where(
                        "invocation_update",
                        lambda e: "completed" in invocation_states_for([e], completed_id),  # noqa: B023
                    )
        finally:
            owner_listener.stop()
            other_listener.stop()

        events = owner_listener.get_events("invocation_update")
        states = invocation_states_for(events, invocation_id)
        assert states[0] == "new", states
        assert "scheduled" in states, states
        assert states.index("scheduled") < states.index("completed"), states
        assert states[-1] == "completed", states
        subworkflow_states = invocation_states_for(events, subworkflow_invocation_id)
        assert "scheduled" in subworkflow_states, subworkflow_states
        assert subworkflow_states[-1] == "completed", subworkflow_states
        assert other_listener.get_events("invocation_update") == []

    def test_owner_receives_cancelling_and_cancelled(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                WORKFLOW_WITH_PAUSE,
                test_data={"test_input": "hello world"},
                history_id=history_id,
                wait=False,
            )
            invocation_id = summary.invocation_id
            # The step after the pause stays delayed, which keeps the invocation ready.
            self.workflow_populator.wait_on_invocation(
                invocation_id,
                lambda: self._invocation_state(invocation_id) == "ready" or None,
                "invocation to be ready",
                DEFAULT_WAIT_TIMEOUT,
            )
            listener = self._listener()
            try:
                self.workflow_populator.cancel_invocation(invocation_id)
                state = self.workflow_populator.wait_for_invocation(None, invocation_id, assert_ok=False)
                listener.wait_for_event_where(
                    "invocation_update", lambda e: "cancelled" in invocation_states_for([e], invocation_id)
                )
            finally:
                listener.stop()

        assert state == "cancelled"
        states = invocation_states_for(listener.get_events("invocation_update"), invocation_id)
        # Events for the earlier transitions to new and ready can arrive after the listener started.
        assert states[states.index("cancelling") :] == ["cancelling", "cancelled"], states


class TestInvocationSSEStepChangesIntegration(BaseInvocationSSEIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["maximum_workflow_jobs_per_scheduling_iteration"] = 1

    def test_scheduling_a_step_of_a_ready_invocation_sends_an_event(self):
        listener = self._listener()
        try:
            with self.dataset_populator.test_history() as history_id:
                summary = self.workflow_populator.run_workflow(
                    WORKFLOW_THREE_INDEPENDENT_STEPS,
                    test_data={"test_input": "hello world"},
                    history_id=history_id,
                    wait=False,
                )
                invocation_id = summary.invocation_id
                self.workflow_populator.wait_for_invocation_and_completion(invocation_id)
                listener.wait_for_event_where(
                    "invocation_update", lambda e: "completed" in invocation_states_for([e], invocation_id)
                )
        finally:
            listener.stop()

        # One job per scheduling iteration: the first iteration makes the invocation ready, and the
        # next schedules another step while it stays ready.
        states = invocation_states_for(listener.get_events("invocation_update"), invocation_id)
        assert states.count("ready") >= 2, states


class TestInvocationSSEViewersIntegration(BaseInvocationSSEIntegrationTestCase):
    def test_viewers_of_accessible_histories_receive_invocation_and_job_updates(self):
        viewer_api_key = self._new_user_api_key()
        outsider_api_key = self._new_user_api_key()
        published_history_id = self.dataset_populator.new_history()
        self.dataset_populator.make_public(published_history_id)
        private_history_id = self.dataset_populator.new_history()

        viewer = self._listener(viewer_api_key)
        outsider = self._listener(outsider_api_key)
        try:
            self._subscribe_as_viewer(viewer_api_key, published_history_id)
            # Skipped: the outsider cannot access the history.
            self._subscribe_as_viewer(outsider_api_key, private_history_id)

            summary = self.workflow_populator.run_workflow(
                WORKFLOW_ONE_STEP,
                test_data={"test_input": "hello world"},
                history_id=published_history_id,
                wait=False,
            )
            invocation_id = summary.invocation_id
            self.workflow_populator.wait_for_invocation_and_completion(invocation_id)
            (job,) = self.dataset_populator.invocation_jobs(invocation_id)
            viewer.wait_for_event_where(
                "invocation_update", lambda e: "completed" in invocation_states_for([e], invocation_id)
            )
            viewer.wait_for_event_where("job_update", lambda e: "ok" in job_states_for([e], job["id"]))

            private_job_id = self.dataset_populator.run_tool("job_properties", {}, private_history_id)["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(private_job_id)
            # Events are delivered in order, so once an event for the outsider's own history arrives,
            # any event for the private history dispatched before it has arrived as well.
            outsider_populator = DatasetPopulator(self._get_interactor(api_key=outsider_api_key))
            outsider_history_id = outsider_populator.new_history()
            outsider_populator.new_dataset(outsider_history_id, wait=False)
            outsider.wait_for_event_where(
                "history_update", lambda e: outsider_history_id in json.loads(e["data"])["history_ids"]
            )
        finally:
            viewer.stop()
            outsider.stop()

        assert job_states_for(outsider.get_events("job_update"), private_job_id) == []
        assert not any(
            private_history_id in json.loads(e["data"])["history_ids"] for e in outsider.get_events("history_update")
        )

    def test_populator_waits_follow_histories_owned_by_others(self):
        viewer_api_key = self._new_user_api_key()
        viewer_interactor = self._get_interactor(api_key=viewer_api_key)
        viewer_dataset_populator = DatasetPopulator(viewer_interactor)
        viewer_workflow_populator = WorkflowPopulator(viewer_interactor)
        published_history_id = self.dataset_populator.new_history()
        self.dataset_populator.make_public(published_history_id)

        summary = self.workflow_populator.run_workflow(
            WORKFLOW_ONE_STEP,
            test_data={"test_input": "hello world"},
            history_id=published_history_id,
            wait=False,
        )
        # The viewer's waits subscribe to the owner's history; without that no event wakes them.
        assert viewer_dataset_populator.wait_for_history(published_history_id) == "ok"
        viewer_workflow_populator.wait_for_invocation_and_completion(summary.invocation_id)
        (job,) = viewer_dataset_populator.invocation_jobs(summary.invocation_id)
        assert viewer_dataset_populator.wait_for_job(job["id"]) == "ok"
