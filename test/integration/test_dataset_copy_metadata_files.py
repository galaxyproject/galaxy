from galaxy_test.api.test_workflows import RunsWorkflowFixtures
from galaxy_test.base.populators import (
    DatasetPopulator,
    wait_on_state,
    WorkflowPopulator,
)
from galaxy_test.driver.integration_util import IntegrationTestCase


class TestDirectoryStrategyMetadataFileIntegrationTestCase(IntegrationTestCase, RunsWorkflowFixtures):
    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["metadata_strategy"] = "directory"

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def test_metadata_copied_to_copied_outputs(self, history_id):
        summary = self.workflow_populator.run_workflow(
            """
class: GalaxyWorkflow
label: Tests metadata copied to copied outputs
inputs:
  bam_file:
    type: collection
    collection_type: list
outputs:
  copied_bam:
    outputSource: extract/output
steps:
  build_list:
    tool_id: __BUILD_LIST__
    in:
      datasets_0|input: bam_file
  sleep:
    tool_id: cat_data_and_sleep
    tool_state:
      sleep_time: 2
    in:
      input1:
        source: build_list/output
  extract:
    tool_id: __EXTRACT_DATASET__
    tool_state:
      which:
        which_dataset: first
    in:
      input:
        source: sleep/out_file1
test_data:
  bam_file:
    value: 1.bam
    file_type: bam
    type: File
""",
            history_id=history_id,
            wait=True,
            assert_ok=True,
        )
        invocation = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
        copied_bam = invocation["outputs"]["copied_bam"]
        dataset = self.dataset_populator.get_history_dataset_details(history_id, content_id=copied_bam["id"])
        assert dataset["peek"] == "Binary bam alignments file"
        assert len(dataset["meta_files"]) == 1

    def test_copy_of_running_output_gets_metadata_and_hidden_source_stays_hidden(self, history_id):
        run = self.dataset_populator.run_tool("all_output_types", {"sleep_param": 5}, history_id)
        output = next(o for o in run["outputs"] if o["output_name"] == "output_tool_supplied_metadata")
        # Copy and hide once the job's outputs were exported for metadata, while the copy's datatype is still "auto"
        job_state = wait_on_state(
            lambda: self.dataset_populator.get_job_details(run["jobs"][0]["id"]),
            skip_states=["new", "queued"],
            timeout=15,
        )
        assert job_state == "running"
        payload = {
            "type": "dataset_collection",
            "collection_type": "list",
            "element_identifiers": [{"name": "element", "src": "hda", "id": output["id"]}],
            "copy_elements": True,
            "hide_source_items": True,
        }
        hdca = self.dataset_populator._post(f"histories/{history_id}/contents", payload, json=True).json()
        self.dataset_populator.wait_for_history_jobs(history_id, assert_ok=True)

        element_id = hdca["elements"][0]["object"]["id"]
        element = self.dataset_populator.get_history_dataset_details(history_id, content_id=element_id)
        assert element["extension"] == "txt"
        assert element["metadata_data_lines"] == 1
        source = self.dataset_populator.get_history_dataset_details(history_id, content_id=output["id"])
        assert source["visible"] is False


class TestExtendedMetadataStrategyMetadataFileIntegrationTestCase(TestDirectoryStrategyMetadataFileIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["metadata_strategy"] = "extended"
