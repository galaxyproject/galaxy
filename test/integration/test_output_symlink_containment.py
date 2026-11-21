"""Tools must not collect outputs through symlinks that lead out of the job directory."""

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

SENTINEL = "outside job directory sentinel"


class BaseOutputSymlinkContainmentIntegrationTestCase(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["retry_metadata_internally"] = False

    def test_from_work_dir_output_cannot_link_outside_job_directory(self):
        self._assert_rejected("from_work_dir_outside")

    def test_from_work_dir_output_can_link_inside_job_directory(self):
        outputs = self._run("from_work_dir_inside", assert_ok=True)
        assert outputs["from_work_dir_output"] == "inside job directory\n"
        assert outputs["output"] == "regular output\n"

    def _assert_rejected(self, link):
        outputs = self._run(link, assert_ok=False)
        assert all(SENTINEL not in content for content in outputs.values())

    def _run(self, link, assert_ok):
        with self.dataset_populator.test_history() as history_id:
            response = self.dataset_populator.run_tool(
                "output_symlink_containment", inputs={"link": link}, history_id=history_id
            )
            job_id = response["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(job_id, assert_ok=assert_ok)
            if not assert_ok:
                job_details = self.dataset_populator.get_job_details(job_id, full=True).json()
                assert job_details["state"] == "error"
                message_types = [message["type"] for message in (job_details.get("job_messages") or [])]
                assert message_types.count("output_collection_security") == 1, message_types
            return {
                output["output_name"]: self.dataset_populator.get_history_dataset_content(
                    history_id, dataset_id=output["id"], assert_ok=False
                )
                for output in response["outputs"]
            }


class BaseOutputsToWorkingDirectorySymlinkContainmentIntegrationTestCase(
    BaseOutputSymlinkContainmentIntegrationTestCase
):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["outputs_to_working_directory"] = True

    def test_named_output_cannot_link_outside_job_directory(self):
        self._assert_rejected("named_outside")

    def test_named_output_can_link_inside_job_directory(self):
        outputs = self._run("named_inside", assert_ok=True)
        assert outputs["output"] == "inside job directory\n"


class TestOutputSymlinkContainmentIntegration(BaseOutputSymlinkContainmentIntegrationTestCase):
    pass


class TestOutputSymlinkContainmentOutputsToWorkingDirectoryIntegration(
    BaseOutputsToWorkingDirectorySymlinkContainmentIntegrationTestCase
):
    pass


class TestOutputSymlinkContainmentExtendedMetadataOutputsToWorkingDirectoryIntegration(
    BaseOutputsToWorkingDirectorySymlinkContainmentIntegrationTestCase
):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["metadata_strategy"] = "extended"
        config["object_store_store_by"] = "uuid"
