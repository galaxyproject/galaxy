import tempfile

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

job_conf_yaml = """
runners:
  local:
    load: galaxy.jobs.runners.pulsar:PulsarRESTJobRunner
    workers: 1
execution:
  default: local
  environments:
    local:
      runner: local
"""


class TestWorkQueuePutFailure(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(
        cls,
        config,
    ):
        super().handle_galaxy_config_kwds(config)
        # config["jobs_directory"] = cls.jobs_directory
        with tempfile.NamedTemporaryFile(mode="w", suffix="job_conf.yml", delete=False) as job_conf:
            job_conf.write(job_conf_yaml)
        config["job_config_file"] = job_conf.name
        # Disable tool dependency resolution.
        config["tool_dependency_dir"] = "none"

    def test_job_fails(self, history_id: str):
        # Set fetch_data to false so we don't bypass the job queue
        self.dataset_populator.new_dataset(history_id, fetch_data=False, content="1 2 3")
        self.dataset_populator.wait_for_history(history_id, assert_ok=False)
        state_details = self.galaxy_interactor.get(f"histories/{history_id}").json()["state_details"]
        assert state_details["running"] == 0
        assert state_details["error"] == 1
