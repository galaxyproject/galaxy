"""Review and cancellation must retain a mapped child's execution context."""

import pytest

from galaxy_test.base.populators import (
    DatasetPopulator,
    wait_on,
    WorkflowPopulator,
)
from galaxy_test.driver import integration_util


class TestSubworkflowPauseMapping(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    @pytest.mark.parametrize("review_action", ["approve", "cancel_child"])
    def test_child_pause_preserves_mapping_and_cancellation(self, review_action):
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                """
class: GalaxyWorkflow
inputs:
  samples:
    type: collection
    collection_type: list
outputs:
  result:
    outputSource: child/result
steps:
  child:
    in:
      sample: samples
    run:
      class: GalaxyWorkflow
      inputs:
        sample: data
      outputs:
        result:
          outputSource: consumer/out_file1
      steps:
        producer:
          tool_id: cat1
          in:
            input1: sample
        review:
          type: pause
          in:
            input: producer/out_file1
        consumer:
          tool_id: cat1
          in:
            input1: review/output
test_data:
  samples:
    collection_type: list
    elements:
      - identifier: X
        content: sample_X
      - identifier: Y
        content: sample_Y
""",
                history_id=history_id,
                wait=False,
            )

            def child_ready_for_review():
                parent = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
                assert parent["state"] not in ("failed", "cancelled"), parent
                child_ids = [
                    step["subworkflow_invocation_id"]
                    for step in parent["steps"]
                    if step.get("subworkflow_invocation_id")
                ]
                if not child_ids:
                    return None
                assert len(child_ids) == 1
                child = self.workflow_populator.get_invocation(child_ids[0], step_details=True)
                assert child["state"] not in ("failed", "cancelled"), child
                steps = {step["workflow_step_label"]: step for step in child["steps"]}
                producer_jobs = steps.get("producer", {}).get("jobs", [])
                if "review" in steps and len(producer_jobs) == 2 and all(job["state"] == "ok" for job in producer_jobs):
                    return child
                return None

            child = wait_on(child_ready_for_review, "mapped child to reach its review pause")
            child_steps = {step["workflow_step_label"]: step for step in child["steps"]}
            assert not child_steps.get("consumer", {}).get("jobs")
            if review_action == "cancel_child":
                self.workflow_populator.cancel_invocation(child["id"])

                def parent_and_child_cancelled():
                    parent = self.workflow_populator.get_invocation(summary.invocation_id)
                    cancelled_child = self.workflow_populator.get_invocation(child["id"], step_details=True)
                    assert parent["state"] != "failed", parent
                    assert cancelled_child["state"] != "failed", cancelled_child
                    if parent["state"] == "cancelled" and cancelled_child["state"] == "cancelled":
                        return cancelled_child
                    return None

                child = wait_on(parent_and_child_cancelled, "parent and mapped child to be cancelled")
                child_steps = {step["workflow_step_label"]: step for step in child["steps"]}
                assert len(child_steps["producer"]["jobs"]) == 2
                assert not child_steps.get("consumer", {}).get("jobs")
                return

            pause_id = child_steps["review"]["id"]
            response = self._put(f"invocations/{child['id']}/steps/{pause_id}", data={"action": True}, json=True)
            self._assert_status_code_is(response, 200)
            self.workflow_populator.wait_for_invocation_and_completion(summary.invocation_id)

            child = self.workflow_populator.get_invocation(child["id"], step_details=True)
            child_steps = {step["workflow_step_label"]: step for step in child["steps"]}
            assert len(child_steps["producer"]["jobs"]) == 2
            assert len(child_steps["consumer"]["jobs"]) == 2

            parent = self.workflow_populator.get_invocation(summary.invocation_id)
            output = self.dataset_populator.get_history_collection_details(
                history_id, content_id=parent["output_collections"]["result"]["id"]
            )
            assert output["collection_type"] == "list"
            assert [element["element_identifier"] for element in output["elements"]] == ["X", "Y"]
            for element, expected in zip(output["elements"], ["sample_X", "sample_Y"]):
                assert element["element_type"] == "hda"
                content = self.dataset_populator.get_history_dataset_content(
                    history_id, dataset_id=element["object"]["id"]
                )
                assert content.strip() == expected
