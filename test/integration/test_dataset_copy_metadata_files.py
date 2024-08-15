from galaxy_test.api.test_workflows import RunsWorkflowFixtures
from galaxy_test.base.populators import (
    DatasetPopulator,
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


class TestExtendedMetadataStrategyMetadataFileIntegrationTestCase(TestDirectoryStrategyMetadataFileIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["metadata_strategy"] = "directory"
