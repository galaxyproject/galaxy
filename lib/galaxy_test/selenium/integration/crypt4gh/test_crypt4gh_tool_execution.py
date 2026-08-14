"""Selenium tests for Crypt4GH tool execution.

Tests verify the decrypt→run→encrypt flow by running the ``cat1`` tool with
crypt4gh-encrypted inputs through the browser, then decrypting outputs to
verify content.
"""

from galaxy_test.selenium.framework import (
    managed_history,
    selenium_test,
    UsesHistoryItemAssertions,
)
from .framework import Crypt4ghIntegrationSeleniumTestCase


class TestCrypt4ghToolExecutionIntegration(Crypt4ghIntegrationSeleniumTestCase, UsesHistoryItemAssertions):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_run_cat_with_single_crypt4gh_input(self):
        """Run cat1 with a single crypt4gh-encrypted input and verify output."""
        # Upload encrypted dataset
        input_details = self.upload_crypt4gh_dataset("1.txt")
        input_hid = input_details["hid"]

        # Open cat1 tool and select the encrypted input
        self.tool_open("cat1")
        self.tool_set_value("input1", f"{input_hid}: ", expected_type="data")
        self.tool_form_execute()

        # Wait for output and verify the wrapped extension once the history item is expanded.
        output_hid = input_hid + 1
        self.assert_crypt4gh_output_extension(output_hid, expected_extension="txt.c4gh")

        # Download, decrypt, and verify content
        output_details = self.dataset_populator.get_history_dataset_details(
            self.current_history_id(),
            hid=output_hid,
        )
        expected_content = self.get_test_file_content("1.txt")
        self.verify_crypt4gh_output(output_details["id"], expected_content)

    @selenium_test
    @managed_history
    def test_run_cat_with_multiple_crypt4gh_inputs(self):
        """Run cat1 with two crypt4gh-encrypted inputs and verify concatenation."""
        # Upload two encrypted datasets
        input1_details = self.upload_crypt4gh_dataset("1.txt")
        input1_hid = input1_details["hid"]

        input2_details = self.upload_crypt4gh_dataset("1.fasta")
        input2_hid = input2_details["hid"]

        # Open cat1 tool, select both inputs
        self.tool_open("cat1")
        self.tool_set_value("input1", f"{input1_hid}: ", expected_type="data")
        # Add a repeat for the second input
        self.components.tool_form.repeat_insert.wait_for_and_click()
        self.tool_set_value("queries_0|input2", f"{input2_hid}: ", expected_type="data")
        self.tool_form_execute()

        # Wait for output and verify the wrapped extension once the history item is expanded.
        output_hid = input2_hid + 1
        self.assert_crypt4gh_output_extension(output_hid, expected_extension="txt.c4gh")

        # Download, decrypt, and verify content is concatenation
        output_details = self.dataset_populator.get_history_dataset_details(
            self.current_history_id(),
            hid=output_hid,
        )
        expected_content = self.get_test_file_content("1.txt") + self.get_test_file_content("1.fasta")
        self.verify_crypt4gh_output(output_details["id"], expected_content)

    @selenium_test
    @managed_history
    def test_run_cat_with_mixed_inputs(self):
        """Run cat1 with one crypt4gh-encrypted and one plain input."""
        # Upload one encrypted and one plain dataset
        enc_details = self.upload_crypt4gh_dataset("1.txt")
        enc_hid = enc_details["hid"]

        plain_details = self.upload_plain_dataset("1.fasta", file_ext="fasta")
        plain_hid = plain_details["hid"]

        # Open cat1 tool, select both inputs
        self.tool_open("cat1")
        self.tool_set_value("input1", f"{enc_hid}: ", expected_type="data")
        self.components.tool_form.repeat_insert.wait_for_and_click()
        self.tool_set_value("queries_0|input2", f"{plain_hid}: ", expected_type="data")
        self.tool_form_execute()

        # Wait for output
        output_hid = plain_hid + 1
        self.history_panel_wait_for_hid_ok(output_hid)

        # Download, decrypt, and verify content
        output_details = self.dataset_populator.get_history_dataset_details(
            self.current_history_id(),
            hid=output_hid,
        )
        expected_content = self.get_test_file_content("1.txt") + self.get_test_file_content("1.fasta")
        self.verify_crypt4gh_output(output_details["id"], expected_content)

    @selenium_test
    @managed_history
    def test_run_cat_without_compute_metadata_fails(self):
        """Run cat1 with a crypt4gh input that has no compute metadata.

        The pre-queue readiness guard should fail the job with an actionable
        error message instead of allowing it to run.
        """
        # Upload encrypted dataset WITHOUT compute metadata
        input_details = self.upload_crypt4gh_dataset("1.txt", set_compute_metadata=False)
        input_hid = input_details["hid"]

        # Open cat1 tool and select the encrypted input
        self.tool_open("cat1")
        self.tool_set_value("input1", f"{input_hid}: ", expected_type="data")
        self.tool_form_execute()

        # The job should fail (not ok) because compute metadata is missing
        output_hid = input_hid + 1
        self.history_panel_wait_for_hid_state(output_hid, "error")
