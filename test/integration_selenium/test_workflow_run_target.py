from galaxy_test.base.workflow_fixtures import WORKFLOW_SIMPLE_CAT_TWICE
from galaxy_test.selenium.framework import (
    managed_history,
    RunsWorkflows,
    UsesHistoryItemAssertions,
)
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)


class WorkflowRunTargetNewSeleniumIntegrationTestCase(
    SeleniumIntegrationTestCase, RunsWorkflows, UsesHistoryItemAssertions
):
    ensure_registered = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["simplified_workflow_run_ui_target_history"] = "new"
        config["simplified_workflow_run_ui"] = "prefer"

    @selenium_test
    @managed_history
    def test_execution_to_new_history(self):
        filename = self.test_data_resolver.get_filename("1.fasta")
        self.perform_upload(filename)
        self.wait_for_history()
        self.workflow_run_open_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        workflow_run = self.components.workflow_run
        workflow_run.expanded_form.wait_for_absent_or_hidden()
        self.workflow_run_submit()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        workflow_run.new_history_target_link.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        workflow_run.new_history_target_link.wait_for_absent_or_hidden()
        self.workflow_run_wait_for_ok(hid=2, expand=True)
        self.assert_item_summary_includes(2, "2 sequences")


class WorkflowRunTargetCurrentSeleniumIntegrationTestCase(
    SeleniumIntegrationTestCase, RunsWorkflows, UsesHistoryItemAssertions
):
    ensure_registered = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["simplified_workflow_run_ui_target_history"] = "current"
        config["simplified_workflow_run_ui"] = "prefer"

    @selenium_test
    @managed_history
    def test_execution_in_current_history(self):
        filename = self.test_data_resolver.get_filename("1.fasta")
        self.perform_upload(filename)
        self.wait_for_history()
        self.workflow_run_open_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        workflow_run = self.components.workflow_run
        workflow_run.expanded_form.wait_for_absent_or_hidden()
        self.workflow_run_submit()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        workflow_run.new_history_target_link.wait_for_absent_or_hidden()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.workflow_run_wait_for_ok(hid=2, expand=True)
        self.assert_item_summary_includes(2, "2 sequences")


class WorkflowRunTargetSelectNewSeleniumIntegrationTestCase(
    SeleniumIntegrationTestCase, RunsWorkflows, UsesHistoryItemAssertions
):
    ensure_registered = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["simplified_workflow_run_ui_target_history"] = "prefer_current"
        config["simplified_workflow_run_ui"] = "prefer"

    @selenium_test
    @managed_history
    def test_execution_in_current_history(self):
        filename = self.test_data_resolver.get_filename("1.fasta")
        self.perform_upload(filename)
        self.wait_for_history()
        self.workflow_run_open_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        workflow_run = self.components.workflow_run
        workflow_run.expanded_form.wait_for_absent_or_hidden()
        workflow_run.runtime_setting_button.wait_for_and_click()
        workflow_run.runtime_setting_target.wait_for_and_click()
        self.send_escape()
        workflow_run.runtime_setting_button.wait_for_and_click()
        workflow_run.runtime_setting_target.wait_for_absent_or_hidden()
        self.workflow_run_submit()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        workflow_run.new_history_target_link.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        workflow_run.new_history_target_link.wait_for_absent_or_hidden()
        self.workflow_run_wait_for_ok(hid=2, expand=True)
        self.assert_item_summary_includes(2, "2 sequences")
