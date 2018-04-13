from base.workflow_fixtures import (
    WORKFLOW_SIMPLE_CAT_TWICE,
    WORKFLOW_WITH_OLD_TOOL_VERSION,
)

from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)


class WorkflowRunTestCase(SeleniumTestCase, UsesHistoryItemAssertions):

    ensure_registered = True

    @selenium_test
    @managed_history
    def test_simple_execution(self):
        self.perform_upload(self.get_filename("1.fasta"))
        self.wait_for_history()
        self.open_in_workflow_run(WORKFLOW_SIMPLE_CAT_TWICE)
        self.screenshot("workflow_run_simple_ready")
        self.workflow_run_submit()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.screenshot("workflow_run_simple_submitted")
        self.history_panel_wait_for_hid_ok(2, allowed_force_refreshes=1)
        self.history_panel_click_item_title(hid=2, wait=True)
        self.assert_item_summary_includes(2, "2 sequences")
        self.screenshot("workflow_run_simple_complete")

    @selenium_test
    def test_execution_with_tool_upgrade(self):
        name = self.workflow_upload_yaml_with_random_name(WORKFLOW_WITH_OLD_TOOL_VERSION, exact_tools=True)
        self.workflow_run_with_name(name)
        self.sleep_for(self.wait_types.UX_TRANSITION)
        # Check that this tool form contains a warning about different versions.
        self.assert_warning_message(contains="different versions")
        self.screenshot("workflow_run_tool_upgrade")

    def open_in_workflow_run(self, yaml_content):
        name = self.workflow_upload_yaml_with_random_name(yaml_content)
        self.workflow_run_with_name(name)

    def workflow_run_with_name(self, name):
        self.workflow_index_open()
        self.workflow_index_search_for(name)
        self.workflow_index_click_option("Run")
