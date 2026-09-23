"""Integration test for the local job runner and cancelling jobs via API."""

import os
import signal
import time

import psutil
from sqlalchemy import select

from galaxy.job_execution.output_collect import default_exit_code_file
from galaxy.job_execution.setup import JobWorkingDirectory
from galaxy.model import Job
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
            lambda: self._get(f"jobs/{job_id}").json()["state"] == "running" or None,
            what="Wait for job to start running",
            maxseconds=60,
        )


class TestLocalJobCancellation(CancelsJob, integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_cancel_job_with_admin_message(self):
        with self.dataset_populator.test_history() as history_id:
            job_id = self._setup_cat_data_and_sleep(history_id)
            self._wait_for_job_running(job_id)
            sa_session = self._app.model.session
            job = self._get_job_by_tool("cat_data_and_sleep")
            # This is how the admin controller code cancels a job
            job.job_stderr = "admin cancelled job"
            job.set_state(Job.states.DELETING)
            sa_session.add(job)
            sa_session.commit()
            self.galaxy_interactor.wait_for(
                lambda: self._get(f"jobs/{job_id}").json()["state"] != "error",
                what="Wait for job to end in error",
                maxseconds=60,
            )

    def test_kill_process(self):
        """ """
        with self.dataset_populator.test_history() as history_id:
            job_id = self._setup_cat_data_and_sleep(history_id)

            sa_session = self._app.model.session
            external_id = None
            state = False

            job = self._get_job_by_tool("cat_data_and_sleep")
            # Not checking the state here allows the change from queued to running to overwrite
            # the change from queued to deleted_new in the API thread - this is a problem because
            # the job will still run. See issue https://github.com/galaxyproject/galaxy/issues/4960.
            while external_id is None or state != Job.states.RUNNING:
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
                if state == Job.states.DELETED:
                    break
                time.sleep(0.1)

            # Now make sure the pid is actually killed.
            for _ in range(100):
                if not pid_exists:
                    break
                pid_exists = psutil.pid_exists(external_id)
                time.sleep(0.1)

            final_state = f"pid exists? {pid_exists}, final db job state {state}"
            assert state == Job.states.DELETED, final_state
            assert not pid_exists, final_state

    def test_intentional_stop_preserves_outputs(self):
        with self.dataset_populator.test_history() as history_id:
            job_id = self._setup_cat_data_and_sleep(history_id)
            self._wait_for_job_running(job_id)
            job = self._get_job_by_tool("cat_data_and_sleep")
            working_directory = JobWorkingDirectory(job, self._app.object_store).resolve()
            self.galaxy_interactor.wait_for(
                lambda: os.path.exists(os.path.join(working_directory, "outputs", "tool_stdout")) or None,
                what="Wait for the tool to start sleeping",
                maxseconds=60,
            )
            assert not os.path.exists(default_exit_code_file(working_directory, job.get_id_tag()))

            # InteractiveToolManager.stop uses this path to end a session and
            # collect its outputs without cancelling or failing the job.
            self._app.job_manager.stop_without_failing(job)

            self.dataset_populator.wait_for_job(job_id, assert_ok=True)
            details = self.dataset_populator.get_job_details(job_id, full=True).json()
            assert details["state"] == Job.states.OK
            assert details["exit_code"] == 0
            assert "job process was killed" not in details["job_stderr"]
            output_id = details["outputs"]["out_file1"]["id"]
            content = self.dataset_populator.get_history_dataset_content(history_id, dataset_id=output_id)
            assert content.strip() == "1 2 3"

    def test_signal_failure_is_reported_in_api_and_database(self):
        with self.dataset_populator.test_history() as history_id:
            job_id = self._setup_cat_data_and_sleep(history_id)
            self._wait_for_job_running(job_id)
            job = self._get_job_by_tool("cat_data_and_sleep")
            os.killpg(int(job.job_runner_external_id), signal.SIGTERM)

            self.dataset_populator.wait_for_job(job_id, assert_ok=False)
            details = self.dataset_populator.get_job_details(job_id, full=True).json()
            message = f"job process was killed by signal {signal.SIGTERM}"
            assert details["state"] == Job.states.ERROR
            assert details["exit_code"] == -signal.SIGTERM
            assert message in details["job_stderr"]

            self._app.model.session.refresh(job)
            assert job.exit_code == -signal.SIGTERM
            assert job.info == message
            assert message in job.job_stderr

    def _get_job_by_tool(self, tool_id):
        stmt = select(Job).filter_by(tool_id=tool_id).order_by(Job.create_time.desc()).limit(1)
        return self._app.model.session.scalars(stmt).first()
