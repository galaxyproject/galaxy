"""Integration test for the local job runner and cancelling jobs via API."""

import time

import psutil

from base import integration_util  # noqa: I202
from base.populators import (
    DatasetPopulator,
)


class LocalJobCancellationTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True

    def setUp(self):
        super(LocalJobCancellationTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_kill_process(self):
        """
        """
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
            running_inputs = {
                "input1": {"src": "hda", "id": hda1["id"]},
                "sleep_time": 240,
            }
            running_response = self.dataset_populator.run_tool(
                "cat_data_and_sleep",
                running_inputs,
                history_id,
                assert_ok=False,
            ).json()
            job_dict = running_response["jobs"][0]

            app = self._app
            sa_session = app.model.context.current
            external_id = None
            state = False

            job = sa_session.query(app.model.Job).filter_by(tool_id="cat_data_and_sleep").one()
            # Not checking the state here allows the change from queued to running to overwrite
            # the change from queued to deleted_new in the API thread - this is a problem because
            # the job will still run. See issue https://github.com/galaxyproject/galaxy/issues/4960.
            while external_id is None or state != app.model.Job.states.RUNNING:
                sa_session.refresh(job)
                assert not job.finished
                external_id = job.job_runner_external_id
                state = job.state

            assert external_id
            external_id = int(external_id)

            pid_exists = psutil.pid_exists(external_id)
            assert pid_exists

            delete_response = self.dataset_populator.cancel_job(job_dict["id"])
            assert delete_response.json() is True

            state = None
            # Now make sure the job becomes complete.
            for i in range(100):
                sa_session.refresh(job)
                state = job.state
                if state == app.model.Job.states.DELETED:
                    break
                time.sleep(.1)

            # Now make sure the pid is actually killed.
            for i in range(100):
                if not pid_exists:
                    break
                pid_exists = psutil.pid_exists(external_id)
                time.sleep(.1)

            final_state = "pid exists? %s, final db job state %s" % (pid_exists, state)
            assert state == app.model.Job.states.DELETED, final_state
            assert not pid_exists, final_state
