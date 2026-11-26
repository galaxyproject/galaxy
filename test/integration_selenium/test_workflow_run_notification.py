from typing import TYPE_CHECKING

from galaxy_test.base.populators import wait_on
from galaxy_test.base.workflow_fixtures import WORKFLOW_SIMPLE_CAT_TWICE
from galaxy_test.selenium.framework import (
    managed_history,
    RunsWorkflows,
    UsesHistoryItemAssertions,
)
from galaxy_test.selenium.upload_activity_helpers import UsesUploadActivity
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)

if TYPE_CHECKING:
    from galaxy_test.selenium.framework import SeleniumSessionDatasetPopulator


class BaseWorkflowRunTargetTestCase(
    SeleniumIntegrationTestCase, RunsWorkflows, UsesHistoryItemAssertions, UsesUploadActivity
):
    dataset_populator: "SeleniumSessionDatasetPopulator"
    ensure_registered = True


class TestWorkflowRunNotificationSeleniumIntegration(BaseWorkflowRunTargetTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_notification_system"] = True
        config["workflow_completion_monitor_sleep"] = 0.1
        config["smtp_server"] = f"mock_emails_to_path://{cls._test_driver.mkdtemp()}"
        config["email_from"] = "galaxy-noreply@example.com"

    @selenium_test
    @managed_history
    def test_on_complete_notification_action(self):
        """Test configuring the send notification completion action."""
        filename = self.test_data_resolver.get_filename("1.fasta")
        self.upload_context("local-file").stage_local_file(filename).start()
        self.wait_for_history()
        self.workflow_run_open_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        self.sleep_for(self.wait_types.UX_RENDER)

        self.find_element_by_selector("[data-test-id='completion-notification-button']").click()
        notification_checkbox = self.find_element_by_selector("[data-test-id='send-notification-checkbox']")
        assert notification_checkbox.is_displayed()
        assert not notification_checkbox.is_selected()
        notification_checkbox.click()
        assert notification_checkbox.is_selected()
        self.screenshot("workflow_run_on_complete_notification_enabled")

        self.find_element_by_selector("[data-test-id='completion-notification-button']").click()
        self.workflow_run_submit()
        self.sleep_for(self.wait_types.UX_TRANSITION)

        history_id = self.current_history_id()
        self.workflow_populator.wait_for_history_workflows(history_id, expected_invocation_count=1)
        invocations = self.workflow_populator.history_invocations(history_id)
        notification = self._wait_for_notification(
            "workflow_execution_completed", f"/workflows/invocations/{invocations[0]['id']}"
        )
        assert notification["content"]["invocation_id"] == invocations[0]["id"]
        assert "ok: 1" in notification["content"]["message"]
        self._assert_notification_visible(notification)

    @selenium_test
    @managed_history
    def test_tool_map_notification_and_saved_delivery_settings(self):
        history_id = self.current_history_id()
        self.dataset_collection_populator.create_list_in_history(history_id, contents=["a\n", "b\n", "c\n"], wait=True)
        self.get("?tool_id=cat1")
        self.components.tool_form.parameter_data_input_collection(parameter="input1").wait_for_and_click()
        self.wait_for_and_click_selector("[data-test-id='completion-notification-button']")
        notification = self.wait_for_selector_visible("[data-test-id='send-notification-checkbox']")
        assert not notification.is_selected()
        notification.click()
        email = self.wait_for_selector_visible("[data-test-id='completion-email-checkbox']")
        assert not email.is_selected()
        email.click()
        wait_on(
            lambda: self.api_get("notifications/preferences")["preferences"]["tool_execution_completed"]["channels"][
                "email"
            ],
            "saved tool email preference",
        )
        self.wait_for_and_click_selector("[data-test-id='completion-notification-button']")
        self.tool_form_execute()
        notification = self._wait_for_notification("tool_execution_completed", f"?id={history_id}")
        assert "3 ok" in notification["content"]["message"]
        self._assert_notification_visible(notification)

        self.get("?tool_id=cat1")
        self.wait_for_and_click_selector("[data-test-id='completion-notification-button']")
        assert not self.wait_for_selector_visible("[data-test-id='send-notification-checkbox']").is_selected()
        assert self.wait_for_selector_visible("[data-test-id='completion-email-checkbox']").is_selected()

    def _wait_for_notification(self, category, link):
        def notifications():
            return [
                notification
                for notification in self.api_get("notifications")
                if notification["category"] == category and link in notification["content"]["message"]
            ] or None

        [notification] = wait_on(notifications, "completion notification")
        return notification

    def _assert_notification_visible(self, notification):
        self.get("user/notifications")
        subject = notification["content"]["subject"]
        self.wait_for_xpath_visible(f'//*[text()[contains(., "{subject}")]]')
