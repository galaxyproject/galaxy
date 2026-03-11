"""Integration tests for job output name length validation."""

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


class TestLongOutputName(integration_util.IntegrationTestCase):
    """Test that jobs with output names exceeding 255 chars fail gracefully."""

    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_short_output_name_succeeds(self):
        with self.dataset_populator.test_history() as history_id:
            response = self.dataset_populator.run_tool(
                "discover_long_name",
                {"output_name": "normal_name"},
                history_id,
            )
            job_id = response["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(job_id, assert_ok=True)

    def _assert_long_name_error(self, job_details):
        assert (
            job_details["state"] == "error"
        ), f"Expected error state, got: {job_details['state']}, details: {job_details}"
        error_message = job_details.get("info", "")
        job_messages = job_details.get("job_messages", [])
        if job_messages:
            error_message += " " + job_messages[0].get("desc", "")
        assert (
            "255 character" in error_message
        ), f"Expected '255 character' in error details, got full details: {job_details}"

    def test_long_output_name_fails_gracefully(self):
        with self.dataset_populator.test_history() as history_id:
            # Use 240 chars: fits within ext4's 255-byte filename limit (240 + 4 for ".txt" = 244),
            # but the association name __new_primary_file_output|<240 chars>__ = 269 chars, exceeding 255.
            long_name = "a" * 240
            response = self.dataset_populator.run_tool(
                "discover_long_name",
                {"output_name": long_name},
                history_id,
            )
            job_id = response["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(job_id, assert_ok=False)
            job_details = self.dataset_populator.get_job_details(job_id, full=True).json()
            self._assert_long_name_error(job_details)


class TestExtendedMetadataLongOutputName(TestLongOutputName):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["metadata_strategy"] = "extended"
        config["object_store_store_by"] = "uuid"
        config["retry_metadata_internally"] = False
