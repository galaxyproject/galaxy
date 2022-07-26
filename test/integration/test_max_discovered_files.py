"""Integration tests for max_discoverd_files setting."""
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


class MaxDiscoveredFilesTestCase(integration_util.IntegrationTestCase):
    """Describe a Galaxy test instance with embedded pulsar configured."""

    framework_tool_and_types = True
    max_discovered_files = 9

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["max_discovered_files"] = cls.max_discovered_files

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_discover(self):
        with self.dataset_populator.test_history() as history_id:
            response = self.dataset_populator.run_tool("discover_sort_by", inputs={}, history_id=history_id)
            job_id = response["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(job_id, assert_ok=False)
            job_details_response = self.dataset_populator.get_job_details(job_id, full=True)
            job_details_response.raise_for_status()
            job_details = job_details_response.json()
            assert job_details["state"] == "error"
            assert (
                f"Job generated more than maximum number ({self.max_discovered_files}) of output datasets"
                in job_details["job_messages"]
            )


class ExtendedMetadataMaxDiscoveredFilesTestCase(MaxDiscoveredFilesTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["max_discovered_files"] = cls.max_discovered_files
        config["metadata_strategy"] = "extended"
