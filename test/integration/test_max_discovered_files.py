"""Integration tests for max_discoverd_files setting."""

from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.base.workflow_fixtures import WORKFLOW_FLAT_CROSS_PRODUCT
from galaxy_test.driver import integration_util


class TestMaxDiscoveredFiles(integration_util.IntegrationTestCase):
    """Describe a Galaxy test instance with embedded pulsar configured."""

    dataset_populator: DatasetPopulator
    framework_tool_and_types = True
    max_discovered_files = 5

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
                in job_details["job_messages"][0]["desc"]
            )

    def test_discover_dynamic_collection_only(self):
        # Regression test for https://github.com/galaxyproject/galaxy/issues/22394.
        with self.dataset_populator.test_history() as history_id:
            response = self.dataset_populator.run_tool(
                "collection_creates_dynamic_list_of_pairs",
                inputs={"foo": "bar"},
                history_id=history_id,
            )
            job_id = response["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(job_id, assert_ok=False)
            job_details_response = self.dataset_populator.get_job_details(job_id, full=True)
            job_details_response.raise_for_status()
            job_details = job_details_response.json()
            assert job_details["state"] == "error"
            assert job_details["job_messages"], "expected a job_messages entry for max_discovered_files"
            job_message = job_details["job_messages"][0]
            assert job_message["type"] == "max_discovered_files"
            assert (
                f"Job generated more than maximum number ({self.max_discovered_files}) of output datasets"
                in job_message["desc"]
            )
            # The dynamic output collection must be marked as failed, not left
            # stuck in 'new'.
            hdca_id = response["output_collections"][0]["id"]
            collection_details = self.dataset_populator.get_history_collection_details(
                history_id, content_id=hdca_id, assert_ok=False
            )
            assert collection_details["populated_state"] == "failed", collection_details


class TestExtendedMetadataMaxDiscoveredFiles(TestMaxDiscoveredFiles):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["max_discovered_files"] = cls.max_discovered_files
        config["metadata_strategy"] = "extended"


class TestMaxDiscoveredFilesCollectionOperations(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True
    max_discovered_files = 5

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["max_discovered_files"] = cls.max_discovered_files

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def test_cross_product_flat(self):
        self._assert_cross_product_rejected("__CROSS_PRODUCT_FLAT__")

    def test_cross_product_nested(self):
        self._assert_cross_product_rejected("__CROSS_PRODUCT_NESTED__")

    def test_cross_product_within_limit(self):
        with self.dataset_populator.test_history() as history_id:
            list_a = self._create_list(history_id, ["a1"])
            list_b = self._create_list(history_id, ["b1", "b2"])
            response = self.dataset_populator.run_tool(
                "__CROSS_PRODUCT_FLAT__",
                inputs={"input_a": {"src": "hdca", "id": list_a}, "input_b": {"src": "hdca", "id": list_b}},
                history_id=history_id,
            )
            self.dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)

    def test_cross_product_in_workflow(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                WORKFLOW_FLAT_CROSS_PRODUCT,
                test_data="""
collection_a:
  collection_type: list
  elements:
    - identifier: a1
      content: a1
    - identifier: a2
      content: a2
collection_b:
  collection_type: list
  elements:
    - identifier: b1
      content: b1
    - identifier: b2
      content: b2
""",
                history_id=history_id,
                assert_ok=False,
                wait=True,
            )
            invocation = self.workflow_populator.get_invocation(summary.invocation_id)
            assert invocation["state"] == "failed"
            message = invocation["messages"][0]
            assert message["reason"] == "unexpected_failure"
            assert (
                f"would create 8 datasets, more than the maximum number ({self.max_discovered_files}) of output datasets"
                in message["details"]
            )

    def test_duplicate_file_to_collection(self):
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="1", wait=True)
            response = self.dataset_populator.run_tool_raw(
                "__DUPLICATE_FILE_TO_COLLECTION__",
                inputs={
                    "input": {"src": "hda", "id": hda["id"]},
                    "number": self.max_discovered_files + 1,
                    "element_identifier": "copy",
                },
                history_id=history_id,
            )
            self._assert_rejected(response, self.max_discovered_files + 1)

    def test_apply_rules_split_columns(self):
        with self.dataset_populator.test_history() as history_id:
            hdca = self._create_list(history_id, ["e0", "e1", "e2"])
            rules = {
                "rules": [
                    {"type": "add_column_metadata", "value": "identifier0"},
                    {"type": "add_column_value", "value": "a"},
                    {"type": "add_column_value", "value": "b"},
                    {"type": "split_columns", "target_columns_0": [1], "target_columns_1": [2]},
                ],
                "mapping": [{"type": "list_identifiers", "columns": [0, 1]}],
            }
            response = self.dataset_populator.run_tool_raw(
                "__APPLY_RULES__",
                inputs={"input": {"src": "hdca", "id": hdca}, "rules": rules},
                history_id=history_id,
            )
            self._assert_rejected(response, 6)

    def test_filter_on_large_collection(self):
        with self.dataset_populator.test_history() as history_id:
            # Uploads are capped by max_discovered_files too, so build the list from individual datasets.
            hdca = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["1"] * (self.max_discovered_files + 1), direct_upload=False
            ).json()["id"]
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            response = self.dataset_populator.run_tool(
                "__FILTER_FAILED_DATASETS__",
                inputs={"input": {"src": "hdca", "id": hdca}},
                history_id=history_id,
            )
            self.dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)

    def _assert_cross_product_rejected(self, tool_id):
        with self.dataset_populator.test_history() as history_id:
            list_a = self._create_list(history_id, ["a1", "a2"])
            list_b = self._create_list(history_id, ["b1", "b2"])
            response = self.dataset_populator.run_tool_raw(
                tool_id,
                inputs={"input_a": {"src": "hdca", "id": list_a}, "input_b": {"src": "hdca", "id": list_b}},
                history_id=history_id,
            )
            self._assert_rejected(response, 8)

    def _create_list(self, history_id, identifiers):
        return self.dataset_collection_populator.create_list_in_history(
            history_id, contents=[(identifier, "1") for identifier in identifiers], wait=True
        ).json()["outputs"][0]["id"]

    def _assert_rejected(self, response, count):
        assert response.status_code == 400, response.text
        assert (
            f"would create {count} datasets, more than the maximum number ({self.max_discovered_files}) of output datasets"
            in response.json()["err_msg"]
        )
