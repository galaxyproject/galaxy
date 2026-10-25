from galaxy.util.unittest_utils import transient_failure
from galaxy_test.base.populators import DatasetPopulator
from .framework import (
    selenium_test,
    SeleniumTestCase,
)
from .upload_activity_helpers import UsesUploadActivity

# Remove hack when submit_login works more consistently.
VALID_LOGIN_RETRIES = 3


class TestHistorySharing(SeleniumTestCase, UsesUploadActivity):
    @selenium_test
    def test_sharing_valid(self):
        user1_email, user2_email, history_id = self.setup_two_users_with_one_shared_history()
        self.submit_login(user2_email, retries=VALID_LOGIN_RETRIES)
        response = self.api_get(f"histories/{history_id}", raw=True)
        assert response.status_code == 200, response.text

    @selenium_test
    def test_sharing_valid_by_id(self):
        user1_email, user2_email, history_id = self.setup_two_users_with_one_shared_history(share_by_id=True)
        self.submit_login(user2_email, retries=VALID_LOGIN_RETRIES)
        response = self.api_get(f"histories/{history_id}", raw=True)
        assert response.status_code == 200, response.text

    @selenium_test
    def test_unsharing(self):
        user1_email, user2_email, history_id = self.setup_two_users_with_one_shared_history()
        self.submit_login(user1_email, retries=VALID_LOGIN_RETRIES)
        self.home()
        self.click_history_option_sharing()
        sharing = self.components.histories.sharing
        self.share_unshare_with_user(sharing, user2_email)

        self.home()
        self.click_history_option_sharing()

        self.share_ensure_by_user_available(sharing)
        unshare_user_button = sharing.unshare_with_user_button(email=user2_email)
        unshare_user_button.assert_absent()

        self.logout_if_needed()
        self.submit_login(user2_email, retries=VALID_LOGIN_RETRIES)
        response = self.api_get(f"histories/{history_id}", raw=True)
        assert response.status_code == 403

    @selenium_test
    def test_unshared_history_inaccessible(self):
        # Here for completeness for now - but probably should have an explict API test case.
        user1_email = self._get_random_email()
        user2_email = self._get_random_email()

        self.register(user1_email)
        history_id = self.current_history_id()
        self.logout_if_needed()

        self.register(user2_email)
        response = self.api_get(f"histories/{history_id}", raw=True)
        assert response.status_code == 403

    @selenium_test
    def test_sharing_with_invalid_user(self):
        user1_email = self._get_random_email()
        self.register(user1_email)
        self.share_history_with_user(user_email="invalid_user@test.com")
        self.assert_error_message(contains="is not a valid Galaxy user")
        self.screenshot("history_sharing_invalid_user")

    @selenium_test
    def test_sharing_with_self(self):
        user1_email = self._get_random_email()
        self.register(user1_email)
        self.share_history_with_user(user_email=user1_email)
        self.assert_error_message(contains="You cannot share resources with yourself")
        self.screenshot("history_sharing_invalid_with_self")

    @selenium_test
    def test_shared_with_me(self):
        user1_email, user2_email, history_id = self.setup_two_users_with_one_shared_history()
        self.submit_login(user2_email, retries=VALID_LOGIN_RETRIES)
        self.navigate_to_histories_shared_with_me_page()
        self.components.shared_histories.shared_list.wait_for_present()
        self.components.shared_histories.history_cards.wait_for_present()
        rows = self.components.shared_histories.history_cards.all()
        assert len(rows) > 0
        assert any(user1_email.split("@")[0] in row.text for row in rows)

    @selenium_test
    def test_unshare_with_me(self):
        [history_id] = self.setup_histories_shared_with_new_user(["History to remove from shared"])
        self.navigate_to_histories_shared_with_me_page()
        shared_histories = self.components.shared_histories
        shared_histories.history_card(history_id=history_id).wait_for_visible()

        shared_histories.extra_actions(history_id=history_id).wait_for_and_click()
        shared_histories.unshare_with_me_button(history_id=history_id).wait_for_and_click()
        assert "from your shared histories" in self.components.confirm_dialog.message.wait_for_text()
        self.screenshot("history_sharing_unshare_with_me_confirm")
        self.components.confirm_dialog.ok_button.wait_for_and_click()

        shared_histories.history_card(history_id=history_id).wait_for_absent()
        self.screenshot("history_sharing_unshare_with_me_removed")
        response = self.api_get(f"histories/{history_id}", raw=True)
        assert response.status_code == 403

    @selenium_test
    def test_bulk_unshare_with_me(self):
        kept_name, *removed_names = ["Kept shared history", "Bulk shared history 1", "Bulk shared history 2"]
        kept_id, *removed_ids = self.setup_histories_shared_with_new_user([kept_name, *removed_names])
        self.navigate_to_histories_shared_with_me_page()
        shared_histories = self.components.shared_histories
        for history_id in [kept_id, *removed_ids]:
            shared_histories.history_card(history_id=history_id).wait_for_visible()

        self.toggle_card_selection_in_list("#history-list", removed_names)
        assert "Remove from Shared (2)" in shared_histories.bulk_unshare_button.wait_for_text()
        shared_histories.bulk_unshare_button.wait_for_and_click()
        assert "Remove 2 histories" in self.components.confirm_dialog.message.wait_for_text()
        self.screenshot("history_sharing_bulk_unshare_with_me_confirm")
        self.components.confirm_dialog.ok_button.wait_for_and_click()

        for history_id in removed_ids:
            shared_histories.history_card(history_id=history_id).wait_for_absent()
            assert self.api_get(f"histories/{history_id}", raw=True).status_code == 403
        shared_histories.history_card(history_id=kept_id).wait_for_visible()
        self.screenshot("history_sharing_bulk_unshare_with_me_removed")

    def setup_histories_shared_with_new_user(self, names):
        """Owner shares one API-created history per name with a new recipient, who stays logged in."""
        self.register(self._get_random_email())
        owner = self.api_interactor_for_logged_in_user()
        owner_populator = DatasetPopulator(owner)
        history_ids = []
        for name in names:
            history_id = owner_populator.new_history(name=name)
            # Can't share an empty history...
            owner_populator.new_dataset(history_id, wait=True)
            history_ids.append(history_id)
        self.logout_if_needed()

        self.register(self._get_random_email())
        recipient_id = self.get_user_id()
        for history_id in history_ids:
            payload = {"user_ids": [recipient_id], "share_option": "make_accessible_to_shared"}
            response = owner.put(f"histories/{history_id}/share_with_users", payload, json=True)
            response.raise_for_status()
            assert [user["id"] for user in response.json()["users_shared_with"]] == [recipient_id]
        return history_ids

    def setup_two_users_with_one_shared_history(self, share_by_id=False):
        user1_email = self._get_random_email()
        user2_email = self._get_random_email()

        self.register(user1_email)
        self.logout_if_needed()
        self.register(user2_email)
        user2_id = None
        if share_by_id:
            user2_id = self.api_get("users")[0]["id"]
        self.logout_if_needed()

        self.submit_login(user1_email, retries=VALID_LOGIN_RETRIES)
        # Can't share an empty history...
        self.upload_context("local-file").stage_local_file(self.get_filename("1.txt")).start()
        self.wait_for_history()

        history_id = self.current_history_id()

        # The uploaded dataset is private, so sharing asks how to change its permissions.
        self.share_history_with_user(
            user_id=user2_id, user_email=user2_email, assert_valid=True, confirm_permissions_change=True
        )
        self.logout_if_needed()

        return user1_email, user2_email, history_id

    def share_history_with_user(
        self, user_id=None, user_email=None, assert_valid=False, screenshot=False, confirm_permissions_change=False
    ):
        """Share the current history with a target user by ID or email.

        ``user_email`` will be used to enter in the share form unless ``user_id``
        is also specified. The ``user_email`` however is always used to check
        the result if ``assert_valid`` is True.
        """
        self.home()
        self.click_history_option_sharing()
        share_kwd = {}
        if screenshot:
            share_kwd["screenshot_before_submit"] = "history_sharing_user_before_submit"
            share_kwd["screenshot_after_submit"] = "history_sharing_user_after_submit"

        self.share_with_user(
            self.components.histories.sharing,
            user_id=user_id,
            user_email=user_email,
            assert_valid=assert_valid,
            confirm_permissions_change=confirm_permissions_change,
            **share_kwd,
        )


class TestHistoryRequiresLoginSelenium(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    def test_share_history_login_redirect(self):
        user_email = self.get_user_email()
        history_id = self.current_history_id()
        self.logout()
        self.go_to_history_sharing(history_id)
        self.assert_error_message(contains="Must be logged in to manage Galaxy items")
        self.components._.messages.require_login.wait_for_and_click()
        self.fill_login_and_submit(user_email)
        self.wait_for_logged_in()
        self.wait_for_selector(".make-accessible")


class TestPrivateHistorySharingRequiresPermissionChanges(SeleniumTestCase, UsesUploadActivity):
    """Test that sharing private histories requires permission changes.

    Includes regression test for PR #20886: When sharing a history containing private datasets
    with another user, the default option should be "Make datasets private to
    me and users this history is shared with" rather than "Make datasets public".
    """

    @transient_failure(issue=21224)
    @selenium_test
    def test_sharing_private_history_default_permission(self):
        # Create two test users - one to own the history, one to share with
        user1_email = self._get_random_email()
        user2_email = self._get_random_email()

        # Register first user and create a private history with data
        self.register(user1_email)
        self.make_history_private()
        self.upload_context("paste-content").stage_paste_content("hello world").start()
        self.wait_for_history()

        # Register second user (must exist to share with)
        self.logout_if_needed()
        self.register(user2_email)
        self.logout_if_needed()

        # Login as first user and initiate sharing
        self.submit_login(user1_email)
        self.home()
        self.click_history_option_sharing()

        # Share with the second user - this triggers the permission dialog
        sharing = self.components.histories.sharing
        self.share_with_user(sharing, user_email=user2_email)

        # Verify the permission change required dialog appears
        self.screenshot("history_private_sharing_permissions_dialog")

        # The next line seems flakey for reasons I don't understand. The data
        # description is attached the model and I do see the modal visually but
        # maybe the modal is not visible because of the modal content or something?
        # At any rate - the following wait would be totally sufficient to ensure
        # the modal is rendered and to continue with the test - so I'm going to
        # just comment out this line and see if it resolves #21224.
        # self.components.histories.sharing.permissions_change_required.wait_for_visible()

        # Verify the default selected option is 'make_accessible_to_shared'
        element = self.components.histories.sharing.permissions_change_required_how.wait_for_visible()
        default_value = element.get_attribute("value")
        assert default_value == "make_accessible_to_shared", (
            f"Expected default permission option to be 'make_accessible_to_shared' "
            f"(private to shared users), but got '{default_value}'"
        )

        # Confirm the permission change to complete sharing
        self.components.histories.sharing.permissions_change_required_ok.wait_for_and_click()
        self.screenshot("history_private_sharing_permissions_confirmed")
