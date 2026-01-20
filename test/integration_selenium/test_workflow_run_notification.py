from typing import TYPE_CHECKING

from selenium.webdriver.common.by import By

from galaxy_test.base.workflow_fixtures import WORKFLOW_SIMPLE_CAT_TWICE
from galaxy_test.selenium.framework import (
    managed_history,
    RunsWorkflows,
    selenium_only,
    UsesHistoryItemAssertions,
)
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)

if TYPE_CHECKING:
    from galaxy_test.selenium.framework import SeleniumSessionDatasetPopulator


class BaseWorkflowRunTargetTestCase(SeleniumIntegrationTestCase, RunsWorkflows, UsesHistoryItemAssertions):
    dataset_populator: "SeleniumSessionDatasetPopulator"
    ensure_registered = True


class TestWorkflowRunNotificationSeleniumIntegration(BaseWorkflowRunTargetTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_notification_system"] = True

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    @managed_history
    def test_on_complete_notification_action(self):
        """Test configuring the send notification completion action."""
        filename = self.test_data_resolver.get_filename("1.fasta")
        self.perform_upload(filename)
        self.wait_for_history()
        self.workflow_run_open_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        self.sleep_for(self.wait_types.UX_RENDER)

        # Open the runtime settings panel by clicking the gear button
        settings_button = self.driver.find_element(By.CSS_SELECTOR, "[data-test-id='workflow-run-settings-button']")
        settings_button.click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("workflow_run_settings_panel_open")

        # Find and click the send notification checkbox
        # GCheckbox root element is a clickable label
        notification_checkbox = self.driver.find_element(By.CSS_SELECTOR, "[data-test-id='send-notification-checkbox']")
        notification_checkbox.click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("workflow_run_on_complete_notification_enabled")

        self.workflow_run_submit()
        self.sleep_for(self.wait_types.UX_TRANSITION)

        # Verify the invocation has the on_complete action
        history_id = self.current_history_id()
        self.workflow_populator.wait_for_history_workflows(history_id, expected_invocation_count=1)
        invocations = self.workflow_populator.history_invocations(history_id)
        invocation = self.workflow_populator.get_invocation(invocations[0]["id"])
        on_complete = invocation.get("on_complete") or []
        assert len(on_complete) == 1, f"Expected 1 on_complete action, got {on_complete}"
        assert "send_notification" in on_complete[0], f"Expected send_notification in {on_complete[0]}"
