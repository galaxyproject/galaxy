from galaxy_test.base.workflow_fixtures import WORKFLOW_SIMPLE_CAT_TWICE
from .framework import (
    selenium_test,
    SeleniumTestCase,
    UsesWorkflowAssertions,
)


class WorkflowSharingRedirectTestCase(SeleniumTestCase):

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


class WorkflowSharingTestCase(SeleniumTestCase, UsesWorkflowAssertions):
    @selenium_test
    def test_sharing_workflow_by_email(self):
        _, user2_email = self.setup_two_users_with_one_shared_workflow(screenshot=True)
        self.submit_login(user2_email)
        self.workflow_index_open()
        # refine this to restrict checking for that workflow so published workflow don't break this test
        self._assert_showing_n_workflows(1)
        self.screenshot("workflow_shared_workflow")

    @selenium_test
    def test_sharing_workflow_by_id(self):
        _, user2_email = self.setup_two_users_with_one_shared_workflow(share_by_id=True)
        self.submit_login(user2_email)
        self.workflow_index_open()
        # refine this to restrict checking for that workflow so published workflow don't break this test
        self._assert_showing_n_workflows(1)

    @selenium_test
    def test_unsharing_workflow(self):
        user1_email, user2_email = self.setup_two_users_with_one_shared_workflow(share_by_id=True)
        self.submit_login(user1_email)
        self.workflow_index_open()
        # refine this to restrict checking for that workflow so published workflow don't break this test
        self._assert_showing_n_workflows(1)
        self.workflow_index_click_option("Share")

        sharing = self.components.histories.sharing
        self.share_unshare_with_user(sharing, user2_email)

        self.home()
        self.workflow_index_open()
        # refine this to restrict checking for that workflow so published workflow don't break this test
        self._assert_showing_n_workflows(1)
        self.workflow_index_click_option("Share")

        self.share_ensure_by_user_available(sharing)
        unshare_user_button = sharing.unshare_with_user_button(email=user2_email)
        unshare_user_button.assert_absent()

        self.logout_if_needed()
        self.submit_login(user2_email)
        self.workflow_index_open()
        self._assert_showing_n_workflows(0)

    @selenium_test
    def test_sharing_with_invalid_user(self):
        user1_email = self._get_random_email()
        self.register(user1_email)
        self._import_workflow_open_sharing()
        self._share_workflow_with_user(
            user_email="invalid_user@test.com",
            assert_valid=False,
        )
        self.assert_error_message(contains="is not a valid Galaxy user")
        self.screenshot("workflow_sharing_invalid_user")

    @selenium_test
    def test_sharing_with_self(self):
        user1_email = self._get_random_email()
        self.register(user1_email)
        self._import_workflow_open_sharing()
        self._share_workflow_with_user(
            user_email=user1_email,
            assert_valid=False,
        )
        self.assert_error_message(contains="You cannot share resources with yourself")
        self.screenshot("workflow_sharing_invalid_sharing_with_self")

    def setup_two_users_with_one_shared_workflow(self, screenshot=False, share_by_id=False):
        user1_email = self._get_random_email()
        user2_email = self._get_random_email()

        self.register(user1_email)
        self.logout_if_needed()
        self.register(user2_email)
        user2_id = None
        if share_by_id:
            user2_id = self.api_get("users")[0]["id"]
        self.logout_if_needed()

        self.submit_login(user1_email)

        self._import_workflow_open_sharing()
        self._share_workflow_with_user(
            user_email=user2_email,
            user_id=user2_id,
            screenshot=screenshot,
            assert_valid=True,
        )

        self.logout_if_needed()

        return user1_email, user2_email

    def _share_workflow_with_user(self, user_id=None, user_email=None, assert_valid=False, screenshot=False):
        kwd = {}
        if screenshot:
            kwd["screenshot_before_submit"] = "workflow_sharing_user_before_submit"
            kwd["screenshot_after_submit"] = "workflow_sharing_user_after_submit"

        self.share_with_user(
            self.components.histories.sharing, user_email=user_email, user_id=user_id, assert_valid=assert_valid, **kwd
        )

    def _import_workflow_open_sharing(self):
        self.workflow_index_open()
        self._workflow_import_from_url()
        self.workflow_index_click_option("Share")
