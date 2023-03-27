from .framework import (
    selenium_test,
    SeleniumTestCase,
)

# Remove hack when submit_login works more consistently.
VALID_LOGIN_RETRIES = 3


class TestHistorySharing(SeleniumTestCase):
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
        self.components.shared_histories.selector.wait_for_present()
        rows = self.components.shared_histories.histories.all()
        assert len(rows) > 0
        assert any(user1_email in row.text for row in rows)

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
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()

        history_id = self.current_history_id()

        self.share_history_with_user(user_id=user2_id, user_email=user2_email, assert_valid=True)
        self.logout_if_needed()

        return user1_email, user2_email, history_id

    def share_history_with_user(self, user_id=None, user_email=None, assert_valid=False, screenshot=False):
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
            **share_kwd,
        )


class TestHistoryRequiresLoginSelenium(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    def test_share_history_login_redirect(self):
        user_email = self.get_logged_in_user()["email"]
        history_id = self.current_history_id()
        self.logout()
        self.go_to_history_sharing(history_id)
        self.assert_error_message(contains="Must be logged in to manage Galaxy items")
        self.components._.messages.require_login.wait_for_and_click()
        self.fill_login_and_submit(user_email)
        self.wait_for_logged_in()
        self.wait_for_selector(".make-accessible")
