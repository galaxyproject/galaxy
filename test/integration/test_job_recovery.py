"""Integration tests for the job recovery after server restarts."""

import os

from galaxy import model
from galaxy.job_execution.setup import JobWorkingDirectory
from galaxy.jobs.runners.pulsar import PulsarJobRunner
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
DELAY_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "delay_job_conf.yml")
PULSAR_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "finishing_recovery_job_conf.yml")
SIMPLE_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "simple_job_conf.xml")


class TestJobRecoveryBeforeHandledIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = SIMPLE_JOB_CONFIG_FILE
        config["server_name"] = "moo"

    def handle_reconfigure_galaxy_config_kwds(self, config) -> None:
        config["server_name"] = "main"

    def test_recovery(self) -> None:
        history_id = self.dataset_populator.new_history()
        self.dataset_populator.run_tool_raw(
            "exit_code_oom",
            {},
            history_id,
        )
        self.restart(handle_reconfig=self.handle_reconfigure_galaxy_config_kwds)
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)


class TestJobRecoveryAfterHandledIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = DELAY_JOB_CONFIG_FILE

    def handle_reconfigure_galaxy_config_kwds(self, config) -> None:
        config["job_config_file"] = SIMPLE_JOB_CONFIG_FILE

    def test_recovery(self) -> None:
        history_id = self.dataset_populator.new_history()
        self.dataset_populator.run_tool_raw(
            "exit_code_oom",
            {},
            history_id,
        )
        self.restart(handle_reconfig=self.handle_reconfigure_galaxy_config_kwds)
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)


class TestPulsarFinishingRecoveryIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = PULSAR_JOB_CONFIG_FILE
        # Preserve the Galaxy-side working directory so the test can recreate
        # the durable state left immediately after Pulsar stages outputs back.
        config["cleanup_job"] = "never"

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_recovery_after_outputs_are_staged_and_remote_job_is_cleaned(self) -> None:
        history_id = self.dataset_populator.new_history()
        response = self.dataset_populator.run_tool("from_work_dir_glob", {}, history_id, assert_ok=True)
        encoded_job_id = response["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(encoded_job_id, assert_ok=True)

        sa_session = self._app.model.session
        job_id = self._app.security.decode_id(encoded_job_id)
        job = sa_session.get(model.Job, job_id)
        assert job is not None
        assert model.Job.states.FINISHING in {state.state for state in job.state_history}
        working_directory = JobWorkingDirectory(job, self._app.object_store).resolve()
        assert os.path.exists(os.path.join(working_directory, f"galaxy_{job.id}.ec"))

        dispatcher = self._app.job_manager.job_handler.dispatcher
        assert dispatcher is not None
        assert job.job_runner_name is not None
        runner = dispatcher.job_runners[job.job_runner_name]
        assert isinstance(runner, PulsarJobRunner)
        runner.get_client(job.destination_params or {}, job.id, external_id=job.get_job_runner_external_id()).clean()

        # Recreate the durable database snapshot a handler restart can leave
        # after staging and remote cleanup but before job_wrapper.finish().
        job.state = model.Job.states.FINISHING
        job.state_history.append(model.JobStateHistory(job=job))
        job.update_output_states(supports_skip_locked=False)
        job.output_datasets[0].dataset.metadata.data_lines = 0
        sa_session.commit()
        sa_session.expire_all()
        assert job.output_datasets[0].dataset.state == model.Dataset.states.SETTING_METADATA

        self.restart()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_populator.wait_for_job(encoded_job_id, assert_ok=True)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        output_details = self.dataset_populator.get_history_dataset_details(
            history_id, dataset=response["outputs"][0], assert_ok=True
        )
        assert output_details["metadata_data_lines"] == 1
