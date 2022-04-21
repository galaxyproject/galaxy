"""Integration test for the local job runner and cancelling jobs via API."""

import time

import psutil

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


class CancelsJob:
    def _setup_cat_data_and_sleep(self, history_id):
        hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
        running_inputs = {
            "input1": {"src": "hda", "id": hda1["id"]},
            "sleep_time": 240,
        }
        running_response = self.dataset_populator.run_tool(
            "cat_data_and_sleep",
            running_inputs,
            history_id,
        )
        job_dict = running_response["jobs"][0]
        return job_dict["id"]

    def _wait_for_job_running(self, job_id):
        self.galaxy_interactor.wait_for(
            lambda: self._get("jobs/%s" % job_id).json()["state"] != "running",
            what="Wait for job to start running",
            maxseconds=60,
        )


class LocalJobCancellationTestCase(CancelsJob, integration_util.IntegrationTestCase):

    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_cancel_job_with_admin_message(self):
        with self.dataset_populator.test_history() as history_id:
            job_id = self._setup_cat_data_and_sleep(history_id)
            self._wait_for_job_running(job_id)
            app = self._app
            sa_session = app.model.context.current
            Job = app.model.Job
            job = sa_session.query(Job).filter_by(tool_id="cat_data_and_sleep").order_by(Job.create_time.desc()).first()
            # This is how the admin controller code cancels a job
            job.job_stderr = "admin cancelled job"
            job.set_state(app.model.Job.states.DELETED_NEW)
            sa_session.add(job)
            sa_session.flush()
            self.galaxy_interactor.wait_for(
                lambda: self._get("jobs/%s" % job_id).json()["state"] != "error",
                what="Wait for job to end in error",
                maxseconds=60,
            )

    def test_kill_process(self):
        """ """
        with self.dataset_populator.test_history() as history_id:
            job_id = self._setup_cat_data_and_sleep(history_id)

            app = self._app
            sa_session = app.model.context.current
            external_id = None
            state = False
            Job = app.model.Job

            job = sa_session.query(Job).filter_by(tool_id="cat_data_and_sleep").order_by(Job.create_time.desc()).first()
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

            delete_response = self.dataset_populator.cancel_job(job_id)
            assert delete_response.json() is True

            state = None
            # Now make sure the job becomes complete.
            for _ in range(100):
                sa_session.refresh(job)
                state = job.state
                if state == app.model.Job.states.DELETED:
                    break
                time.sleep(0.1)

            # Now make sure the pid is actually killed.
            for _ in range(100):
                if not pid_exists:
                    break
                pid_exists = psutil.pid_exists(external_id)
                time.sleep(0.1)

            final_state = f"pid exists? {pid_exists}, final db job state {state}"
            assert state == app.model.Job.states.DELETED, final_state
            assert not pid_exists, final_state
