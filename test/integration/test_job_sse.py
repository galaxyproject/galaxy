"""Integration tests for ``job_update`` SSE events on job state changes.

The populator job waits re-check jobs only when a ``job_update`` event arrives once the server
has SSE updates enabled, so every wait here also asserts that the event was sent.
"""

from uuid import uuid4

from galaxy_test.base.sse import (
    DEFAULT_WAIT_TIMEOUT,
    job_states_for,
)
from galaxy_test.driver.integration_util import SSEIntegrationTestCase

WORKFLOW_WITH_SLOW_STEP = """
class: GalaxyWorkflow
inputs:
  test_input: data
steps:
  slow_step:
    tool_id: job_properties
    state:
      sleepsecs: 60
"""


class TestJobSSEIntegration(SSEIntegrationTestCase):
    def _job_state(self, job_id: str) -> str:
        return self.dataset_populator.get_job_details(job_id).json()["state"]

    def test_owner_receives_job_states(self):
        other_user = self._setup_user(f"{uuid4()}@galaxy.test")
        _, other_api_key = self._setup_user_get_key(other_user["email"])

        with self.dataset_populator.test_history() as history_id:
            owner_listener = self._listener()
            other_listener = self._listener(other_api_key)
            try:
                run = self.dataset_populator.run_tool("job_properties", {"sleepsecs": 1}, history_id)
                job_id = run["jobs"][0]["id"]
                state = self.dataset_populator.wait_for_job(job_id)
                # The wait can see the committed state before the event reaches this listener.
                owner_listener.wait_for_event_where("job_update", lambda e: "ok" in job_states_for([e], job_id))
            finally:
                owner_listener.stop()
                other_listener.stop()

        assert state == "ok"
        states = job_states_for(owner_listener.get_events("job_update"), job_id)
        assert states[0] == "new", states
        assert "running" in states, states
        assert states[-1] == "ok", states
        assert other_listener.get_events("job_update") == []

    def test_owner_receives_job_failure(self):
        with self.dataset_populator.test_history() as history_id:
            listener = self._listener()
            try:
                run = self.dataset_populator.run_tool("job_properties", {"failbool": True}, history_id)
                job_id = run["jobs"][0]["id"]
                state = self.dataset_populator.wait_for_job(job_id)
                listener.wait_for_event_where("job_update", lambda e: "error" in job_states_for([e], job_id))
            finally:
                listener.stop()

        assert state == "error"
        assert job_states_for(listener.get_events("job_update"), job_id)[-1] == "error"

    def test_cancelling_an_invocation_sends_its_job_deleting(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                WORKFLOW_WITH_SLOW_STEP,
                test_data={"test_input": "hello world"},
                history_id=history_id,
                wait=False,
            )
            invocation_id = summary.invocation_id
            self.workflow_populator.wait_for_invocation(None, invocation_id)
            (job,) = self.dataset_populator.invocation_jobs(invocation_id)
            job_id = job["id"]
            self.dataset_populator.wait_on_job_update(
                job_id,
                lambda: self._job_state(job_id) == "running" or None,
                "job to run",
                DEFAULT_WAIT_TIMEOUT,
            )
            listener = self._listener()
            try:
                self.workflow_populator.cancel_invocation(invocation_id)
                self.dataset_populator.wait_on_job_update(
                    job_id,
                    lambda: self._job_state(job_id) in ("deleted", "deleting") or None,
                    "job to be deleted",
                    DEFAULT_WAIT_TIMEOUT,
                )
                # The invocation's scheduler marks running jobs deleting with a bulk UPDATE. Events for
                # the job's earlier states can still arrive first, so wait for this one specifically.
                listener.wait_for_event_where("job_update", lambda e: "deleting" in job_states_for([e], job_id))
            finally:
                listener.stop()
