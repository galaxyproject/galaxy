"""Integration tests for GalaxyInteractor."""

import pytest
from packaging.version import Version

from galaxy.tool_util.parser.interface import TestCollectionOutputDef
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
)
from galaxy_test.driver import integration_util

POPULATION_FAIL_TOOL = "collection_creates_dynamic_population_fail"


class TestGalaxyInteractor(integration_util.IntegrationTestCase):
    framework_tool_and_types = True
    dataset_populator: DatasetPopulator
    dataset_collection_populator: DatasetCollectionPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def test_local_test_data_download(self):
        self.galaxy_interactor._target_galaxy_version = Version("18.09")
        assert self.galaxy_interactor.supports_test_data_download is False
        assert self.galaxy_interactor.test_data_download(tool_id="cat1", filename="1.bed").startswith(
            b"chr1\t147962192\t147962580"
        )

    def test_run_test_select_version(self):
        self._run_tool_test(tool_id="multiple_versions", tool_version="0.1")

    def test_get_tool_tests(self):
        # test that get_tool_tests will return the right tests when the tool_version has a '+' in it
        test_data = self.galaxy_interactor.get_tool_tests(tool_id="multiple_versions", tool_version="0.1+galaxy6")
        assert isinstance(test_data, list)
        assert len(test_data) > 0
        test_data_dict = test_data[0]
        assert isinstance(test_data_dict, dict)
        assert test_data_dict.get("tool_version") == "0.1+galaxy6"

        test_data = self.galaxy_interactor.get_tool_tests(
            tool_id="multiple_versions"
        )  # test that tool_version=None does not break it
        assert isinstance(test_data, list)
        assert len(test_data) > 0
        test_data_dict = test_data[0]
        assert isinstance(test_data_dict, dict)

    def test_verify_collection_rejects_failed_discovery(self):
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="a\n", file_type="txt", wait=True)
            inputs = {"input1": {"src": "hda", "id": hda["id"]}}
            response = self.dataset_populator.run_tool(POPULATION_FAIL_TOOL, inputs, history_id)
            error = self._verify_population_failure(response, response["output_collections"][0]["id"], history_id)
            assert error == (
                "Output collection 'list_output': populated state is 'failed', expected 'ok'. "
                "Problem building datasets for collection."
            )

    def test_verify_collection_rejects_failed_mapped_over_discovery(self):
        with self.dataset_populator.test_history() as history_id:
            hdca = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=[("sample1", "a\n")], direct_upload=True, wait=True
            ).json()["output_collections"][0]
            inputs = {"input1": {"batch": True, "values": [{"src": "hdca", "id": hdca["id"]}]}}
            response = self.dataset_populator.run_tool(POPULATION_FAIL_TOOL, inputs, history_id)
            error = self._verify_population_failure(response, response["implicit_collections"][0]["id"], history_id)
            assert error == "Output collection 'list_output/sample1': collection is not populated."

    def _verify_population_failure(self, tool_response, output_collection_id, history_id) -> str:
        for job in tool_response["jobs"]:
            self.dataset_populator.wait_for_job(job["id"], assert_ok=True)
        output_def = TestCollectionOutputDef.from_dict({"name": "list_output"})
        with pytest.raises(AssertionError) as exc_info:
            self.galaxy_interactor.verify_output_collection(
                output_def, output_collection_id, history_id, POPULATION_FAIL_TOOL
            )
        return str(exc_info.value)
