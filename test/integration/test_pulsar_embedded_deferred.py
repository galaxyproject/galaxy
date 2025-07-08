import os

from galaxy_test.base.populators import (
    DatasetPopulator,
    skip_without_tool,
)
from galaxy_test.driver import integration_util
from .test_containerized_jobs import disable_dependency_resolution

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_job_conf.yml")


class TestEmbeddedPulsarDeferredDataIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    job_config_file: str
    jobs_directory: str
    framework_tool_and_types = True
    job_config_file = EMBEDDED_PULSAR_JOB_CONFIG_FILE

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        cls.jobs_directory = cls._test_driver.mkdtemp()
        config["jobs_directory"] = cls.jobs_directory
        config["job_config_file"] = cls.job_config_file
        disable_dependency_resolution(config)

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @skip_without_tool("cat")
    def test_run_deferred_dataset(self, history_id):
        with self.dataset_populator.test_history_for(self.test_run_deferred_dataset) as history_id:
            base64_url = self.dataset_populator.base64_url_for_test_file("1.bed")
            details = self.dataset_populator.create_deferred_hda(history_id, base64_url, ext="bed")
            input1 = dict(src="hda", id=details["id"])
            inputs = {
                "input1": input1,
            }
            job_response = self.dataset_populator.run_tool(
                "cat",
                inputs=inputs,
                history_id=history_id,
                assert_ok=True,
                assert_has_job=True,
                wait=True,
            )
            outputs = job_response["outputs"]
            assert len(outputs) == 1
            output = outputs[0]
            details = self.dataset_populator.get_history_dataset_details(
                history_id, dataset=output, wait=True, assert_ok=True
            )
            assert details["state"] == "ok"
            output_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output)
            assert output_content.startswith("chr1	147962192	147962580	CCDS989.1_cds_0_0_chr1_147962193_r	0	-")
