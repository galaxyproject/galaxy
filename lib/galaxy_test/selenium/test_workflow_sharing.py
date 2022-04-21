from galaxy_test.base.workflow_fixtures import WORKFLOW_SIMPLE_CAT_TWICE
from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class WorkflowSharingTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_share_workflow_with_login_redirect(self):
        user_email = self.get_logged_in_user()["email"]
        workflow_id = self.workflow_populator.upload_yaml_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        self.logout()
        self.go_to_workflow_sharing(workflow_id)
        self.assert_error_message(contains="Must be logged in to manage Galaxy items")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.components._.messages.require_login.wait_for_and_click()
        self.fill_login_and_submit(user_email)
        self.wait_for_logged_in()
        self.wait_for_selector(".make-accessible")

    @selenium_test
    def test_export_workflow_with_login_redirect(self):
        user_email = self.get_logged_in_user()["email"]
        workflow_id = self.workflow_populator.upload_yaml_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        self.logout()
        self.go_to_workflow_export(workflow_id)
        self.assert_error_message(contains="You must be logged in to export Galaxy workflows.")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.components._.messages.require_login.wait_for_and_click()
        self.fill_login_and_submit(user_email)
        self.wait_for_logged_in()
