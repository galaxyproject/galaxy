"""Integration tests for ``invocation_update`` SSE events on workflow invocation changes.

The populator waits re-check invocations only when an ``invocation_update`` event for them
arrives once the server has SSE updates enabled, so every wait here also asserts that the
event was sent.
"""

import json
from urllib.parse import urljoin
from uuid import uuid4

from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.base.sse import (
    DEFAULT_WAIT_TIMEOUT,
    SSELineListener,
)
from galaxy_test.base.workflow_fixtures import WORKFLOW_NESTED_SIMPLE
from galaxy_test.driver.integration_util import IntegrationTestCase

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


def _states_for(events: list[dict], invocation_id: str) -> list[str]:
    return [
        invocation["state"]
        for event in events
        for invocation in json.loads(event["data"])["invocations"]
        if invocation["id"] == invocation_id
    ]


class BaseInvocationSSEIntegrationTestCase(IntegrationTestCase):
    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_sse_updates"] = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def _listener(self, api_key: str | None = None) -> SSELineListener:
        api_key = api_key or self.galaxy_interactor.api_key
        assert api_key is not None
        listener = SSELineListener(urljoin(self.url, "api/events/stream"), api_key)
        listener.start()
        return listener

    def _invocation_state(self, invocation_id: str) -> str:
        return self.workflow_populator.get_invocation(invocation_id)["state"]


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
                        lambda e: "completed" in _states_for([e], completed_id),  # noqa: B023
                    )
        finally:
            owner_listener.stop()
            other_listener.stop()

        events = owner_listener.get_events("invocation_update")
        states = _states_for(events, invocation_id)
        assert states[0] == "new", states
        assert "scheduled" in states, states
        assert states.index("scheduled") < states.index("completed"), states
        assert states[-1] == "completed", states
        subworkflow_states = _states_for(events, subworkflow_invocation_id)
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
                    "invocation_update", lambda e: "cancelled" in _states_for([e], invocation_id)
                )
            finally:
                listener.stop()

        assert state == "cancelled"
        assert _states_for(listener.get_events("invocation_update"), invocation_id) == ["cancelling", "cancelled"]


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
                    "invocation_update", lambda e: "completed" in _states_for([e], invocation_id)
                )
        finally:
            listener.stop()

        # One job per scheduling iteration: the first iteration makes the invocation ready, and the
        # next schedules another step while it stays ready.
        states = _states_for(listener.get_events("invocation_update"), invocation_id)
        assert states.count("ready") >= 2, states
