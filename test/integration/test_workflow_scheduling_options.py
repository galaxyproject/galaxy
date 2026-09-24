"""Integration tests for workflow scheduling configuration option."""

import time
from json import dumps
from pathlib import Path

import yaml

from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.base.workflow_fixtures import WORKFLOW_WITH_OUTPUT_COLLECTION_MAPPING
from galaxy_test.driver import integration_util


class TestMaximumWorkflowInvocationDuration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["maximum_workflow_invocation_duration"] = 20

    def test(self):
        workflow = self.workflow_populator.load_workflow_from_resource("test_workflow_pause")
        workflow_id = self.workflow_populator.create_workflow(workflow)
        history_id = self.dataset_populator.new_history()
        hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
        index_map = {"0": dict(src="hda", id=hda1["id"])}
        request = {}
        request["history"] = f"hist_id={history_id}"
        request["inputs"] = dumps(index_map)
        request["inputs_by"] = "step_index"
        url = f"workflows/{workflow_id}/invocations"
        invocation_response = self._post(url, data=request, json=True)
        invocation_url = url + "/" + invocation_response.json()["id"]
        time.sleep(5)
        state = self._get(invocation_url).json()["state"]
        assert state != "failed", state
        time.sleep(35)
        state = self._get(invocation_url).json()["state"]
        assert state == "failed", state


class TestMaximumWorkflowJobsPerSchedulingIteration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["maximum_workflow_jobs_per_scheduling_iteration"] = 1

    def test_collection_explicit_and_implicit(self):
        workflow_id = self.workflow_populator.upload_yaml_workflow(WORKFLOW_WITH_OUTPUT_COLLECTION_MAPPING)
        with self.dataset_populator.test_history() as history_id:
            fetch_response = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["a\nb\nc\nd\n", "e\nf\ng\nh\n"]
            ).json()
            hdca1 = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            inputs = {
                "0": {"src": "hdca", "id": hdca1["id"]},
            }
            self.workflow_populator.invoke_workflow_and_wait(workflow_id, history_id, inputs)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            assert "a\nc\nb\nd\ne\ng\nf\nh\n" == self.dataset_populator.get_history_dataset_content(history_id, hid=0)

    def test_subworkflow_mapping_axes_survive_scheduling_rounds(self):
        workflow_path = (
            Path(__file__).parents[2] / "lib" / "galaxy_test" / "workflow" / "subworkflow_mapping_per_step.gxwf.yml"
        )
        tests_path = workflow_path.with_name("subworkflow_mapping_per_step.gxwf-tests.yml")
        with tests_path.open() as tests_file:
            test_job = yaml.safe_load(tests_file)[0]["job"]

        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                str(workflow_path),
                test_data=test_job,
                history_id=history_id,
                source_type="path",
                wait=True,
            )
            parent_invocation = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
            child_invocation_ids = {
                step["subworkflow_invocation_id"]
                for step in parent_invocation["steps"]
                if step.get("subworkflow_invocation_id")
            }
            assert len(child_invocation_ids) == 1

            child_invocation = self.workflow_populator.get_invocation(child_invocation_ids.pop(), step_details=True)
            child_steps = {step["workflow_step_label"]: step for step in child_invocation["steps"]}
            assert len(child_steps["cat_mixed_mapping_sources"]["jobs"]) == 6
            assert len(child_steps["cat_chained_mapping_output"]["jobs"]) == 6
            assert len(child_steps["cat_after_pick_value"]["jobs"]) == 6
            assert len(child_steps["cat_zip_chained_outputs"]["jobs"]) == 6
            assert len(child_steps["consume_mapped_output_as_collection"]["jobs"]) == 2
            assert len(child_steps["consume_pair_elements"]["jobs"]) == 4

            output_id = parent_invocation["output_collections"]["chained_pick_value_output"]["id"]
            output = self.dataset_populator.get_history_collection_details(history_id, content_id=output_id)
            assert output["collection_type"] == "list:list"
            assert len(output["elements"]) == 2
            assert all(len(element["object"]["elements"]) == 3 for element in output["elements"])

            passthrough_id = parent_invocation["output_collections"]["direct_collection_passthrough"]["id"]
            passthrough = self.dataset_populator.get_history_collection_details(history_id, content_id=passthrough_id)
            assert passthrough["collection_type"] == "list:list"
            assert [element["element_identifier"] for element in passthrough["elements"]] == ["X", "Y"]
            assert all(
                [leaf["element_identifier"] for leaf in outer["object"]["elements"]] == ["P", "Q", "R"]
                for outer in passthrough["elements"]
            )

            direct_dataset_id = parent_invocation["output_collections"]["direct_dataset_passthrough"]["id"]
            direct_dataset = self.dataset_populator.get_history_collection_details(
                history_id, content_id=direct_dataset_id
            )
            assert direct_dataset["collection_type"] == "list"
            assert len({element["object"]["id"] for element in direct_dataset["elements"]}) == 1

            # Pass-through outputs become available before the child's tool
            # outputs. Delayed scheduling retries must not re-materialize and
            # leak a fresh history collection on every retry.
            history_contents = self.dataset_populator.get_history_contents(history_id)
            history_collection_names = [
                item["name"] for item in history_contents if item["history_content_type"] == "dataset_collection"
            ]
            assert history_collection_names.count("sub: direct_collection_passthrough") == 1
            assert history_collection_names.count("sub: direct_dataset_passthrough") == 1

    def test_conditional_subworkflow_passthrough_is_materialized_once(self):
        with self.dataset_populator.test_history() as history_id:
            self.workflow_populator.run_workflow(
                """
class: GalaxyWorkflow
inputs:
  boolean_input_files: collection
  direct_dataset: data
steps:
  create_list_of_boolean:
    tool_id: param_value_from_file
    in:
      input1: boolean_input_files
    state:
      param_type: boolean
  subworkflow:
    run:
      class: GalaxyWorkflow
      inputs:
        boolean_input_file: data
        should_run: boolean
        direct_dataset: data
      steps:
        consume_expression_parameter:
          tool_id: cat1
          in:
            input1: boolean_input_file
      outputs:
        inner_output:
          outputSource: consume_expression_parameter/out_file1
        direct_dataset_passthrough:
          outputSource: direct_dataset/output
    in:
      boolean_input_file: boolean_input_files
      should_run: create_list_of_boolean/boolean_param
      direct_dataset: direct_dataset
    when: $(inputs.should_run)
outputs:
  inner_output:
    outputSource: subworkflow/inner_output
  direct_dataset_passthrough:
    outputSource: subworkflow/direct_dataset_passthrough
""",
                test_data="""
boolean_input_files:
  collection_type: list
  elements:
    - identifier: true
      content: true
    - identifier: false
      content: false
direct_dataset:
  value: 1.bed
  type: File
""",
                history_id=history_id,
            )

            history_contents = self.dataset_populator.get_history_contents(history_id)
            skipped_passthroughs = [
                item
                for item in history_contents
                if item["history_content_type"] == "dataset" and item["name"] == "Subworkflow pass-through - skipped"
            ]
            assert len(skipped_passthroughs) == 1

    def test_scheduling_rounds(self):
        with self.dataset_populator.test_history() as history_id:
            invocation_response = self.workflow_populator.run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input1: data
  text_input: text
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: input1
  second_cat:
    tool_id: cat1
    in:
      input1: first_cat/out_file1
  collection_creates_dynamic_list_of_pairs:
    tool_id: collection_creates_dynamic_list_of_pairs
    in:
      file: second_cat/out_file1
  count_multi_file:
    tool_id: count_multi_file
    in:
      input1: collection_creates_dynamic_list_of_pairs/list_output
outputs:
  wf_output_1:
    outputSource: collection_creates_dynamic_list_of_pairs/list_output
""",
                test_data="""
input1:
  value: 1.fasta
  type: File
  name: fasta1
text_input: foo
""",
                history_id=history_id,
            )
            invocation = self._get(f"invocations/{invocation_response.invocation_id}").json()
            assert "wf_output_1" in invocation["output_collections"]
