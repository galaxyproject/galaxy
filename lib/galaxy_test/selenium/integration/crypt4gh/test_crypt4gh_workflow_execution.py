"""Selenium tests for Crypt4GH workflow execution.

Tests verify the decrypt→run→encrypt flow through multi-step workflows with
crypt4gh-encrypted inputs, then decrypting outputs to verify content.
"""

from galaxy_test.selenium.framework import (
    managed_history,
    RunsWorkflows,
    selenium_test,
    UsesHistoryItemAssertions,
)
from .framework import Crypt4ghIntegrationSeleniumTestCase

# Workflow with a single cat1 step that concatenates the input with itself.
# (WORKFLOW_SIMPLE_CAT_TWICE from workflow_fixtures.py is this exact pattern.)
WORKFLOW_SIMPLE_CAT_TWICE = """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: input1
      queries_0|input2: input1
"""

# Two-step workflow: first cat1 concatenates input1 + input2, second cat1
# concatenates the result with input1 again.
WORKFLOW_TWO_STEP_CAT = """
class: GalaxyWorkflow
inputs:
  input1: data
  input2: data
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: input1
      queries_0|input2: input2
  second_cat:
    tool_id: cat1
    in:
      input1: first_cat/out_file1
      queries_0|input2: input1
"""


class TestCrypt4ghWorkflowExecutionIntegration(
    Crypt4ghIntegrationSeleniumTestCase, RunsWorkflows, UsesHistoryItemAssertions
):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_simple_cat_workflow(self):
        """Run a single-step cat1 workflow with one crypt4gh-encrypted input.

        The workflow concatenates the input with itself, so the output should
        be the input content doubled.
        """
        input_details = self.upload_crypt4gh_dataset("1.txt")
        input_hid = input_details["hid"]

        # Open and run the workflow
        self.workflow_run_open_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        self.workflow_run_submit()
        self.sleep_for(self.wait_types.UX_TRANSITION)

        # Wait for output (input_hid + 1 since there's one input and one output)
        output_hid = input_hid + 1
        self.workflow_run_wait_for_ok(output_hid, expand=True)
        self.assert_crypt4gh_output_extension(output_hid, expected_extension="txt.c4gh")

        # Download, decrypt, and verify content (doubled input)
        output_details = self.dataset_populator.get_history_dataset_details(
            self.current_history_id(),
            hid=output_hid,
        )
        expected_content = self.get_test_file_content("1.txt") * 2
        self.verify_crypt4gh_output(output_details["id"], expected_content)

    @selenium_test
    @managed_history
    def test_multi_step_workflow_with_multiple_inputs(self):
        """Run a two-step cat1 workflow with two crypt4gh-encrypted inputs.

        Step 1: cat1(input1, input2) → intermediate
        Step 2: cat1(intermediate, input1) → final output
        """
        input1_details = self.upload_crypt4gh_dataset("1.txt")
        input1_hid = input1_details["hid"]

        input2_details = self.upload_crypt4gh_dataset("1.fasta")
        input2_hid = input2_details["hid"]

        # Open and run the workflow, specifying inputs
        self.workflow_run_open_workflow(WORKFLOW_TWO_STEP_CAT)
        self.workflow_run_specify_inputs(
            {
                "input1": {"hid": input1_hid},
                "input2": {"hid": input2_hid},
            }
        )
        self.workflow_run_submit()
        self.sleep_for(self.wait_types.UX_TRANSITION)

        # Wait for output (two inputs + two steps → output is last hid)
        output_hid = input2_hid + 2
        self.workflow_run_wait_for_ok(output_hid, expand=True)
        self.assert_crypt4gh_output_extension(output_hid, expected_extension="txt.c4gh")

        # Download, decrypt, and verify content
        # Step 1: 1.txt + 1.fasta
        # Step 2: (1.txt + 1.fasta) + 1.txt
        content_1_txt = self.get_test_file_content("1.txt")
        content_1_fasta = self.get_test_file_content("1.fasta")
        expected_content = content_1_txt + content_1_fasta + content_1_txt
        output_details = self.dataset_populator.get_history_dataset_details(
            self.current_history_id(),
            hid=output_hid,
        )
        self.verify_crypt4gh_output(output_details["id"], expected_content)

    @selenium_test
    @managed_history
    def test_workflow_with_mixed_inputs(self):
        """Run a two-step cat1 workflow with one crypt4gh and one plain input."""
        enc_details = self.upload_crypt4gh_dataset("1.txt")
        enc_hid = enc_details["hid"]

        plain_details = self.upload_plain_dataset("1.fasta", file_ext="fasta")
        plain_hid = plain_details["hid"]

        # Open and run the workflow, specifying inputs
        self.workflow_run_open_workflow(WORKFLOW_TWO_STEP_CAT)
        self.workflow_run_specify_inputs(
            {
                "input1": {"hid": enc_hid},
                "input2": {"hid": plain_hid},
            }
        )
        self.workflow_run_submit()
        self.sleep_for(self.wait_types.UX_TRANSITION)

        # Wait for output
        output_hid = plain_hid + 2
        self.workflow_run_wait_for_ok(output_hid, expand=True)
        self.assert_crypt4gh_output_extension(output_hid, expected_extension="txt.c4gh")

        # Download, decrypt, and verify content
        # Step 1: 1.txt + 1.fasta
        # Step 2: (1.txt + 1.fasta) + 1.txt
        content_1_txt = self.get_test_file_content("1.txt")
        content_1_fasta = self.get_test_file_content("1.fasta")
        expected_content = content_1_txt + content_1_fasta + content_1_txt
        output_details = self.dataset_populator.get_history_dataset_details(
            self.current_history_id(),
            hid=output_hid,
        )
        self.verify_crypt4gh_output(output_details["id"], expected_content)
