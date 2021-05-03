from .framework import (
    selenium_test,
    SeleniumTestCase
)

# Remove hack when submit_login works more consistently.
VALID_LOGIN_RETRIES = 3


class HistorySharingTestCase(SeleniumTestCase):

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
        self.navigate_to_history_share_page()

        unshare_user_button = self.components.histories.sharing.unshare_user_button
        unshare_user_button.wait_for_and_click()

        self.navigate_to_history_share_page()
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
        self.assert_error_message(contains='is not a valid Galaxy user')

    @selenium_test
    def test_sharing_with_self(self):
        user1_email = self._get_random_email()
        self.register(user1_email)
        self.share_history_with_user(user_email=user1_email)
        self.assert_error_message(contains='You cannot share resources with yourself')

    def setup_two_users_with_one_shared_history(self, share_by_id=False):
        user1_email = self._get_random_email()
        user2_email = self._get_random_email()

        self.register(user1_email)
        self.logout_if_needed()
        self.register(user2_email)
        user2_id = self.api_get("users")[0]["id"]
        self.logout_if_needed()

        self.submit_login(user1_email, retries=VALID_LOGIN_RETRIES)
        # Can't share an empty history...
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()

        history_id = self.current_history_id()

        if share_by_id:
            self.share_history_with_user(user_email=user2_email, assert_valid=True)
        else:
            self.share_history_with_user(user_id=user2_id, user_email=user2_email, assert_valid=True)
        self.logout_if_needed()

        return user1_email, user2_email, history_id

    def navigate_to_history_share_page(self):
        self.home()
        self.click_history_option("Share or Publish")

    def share_history_with_user(self, user_id=None, user_email=None, assert_valid=False, screenshot=False):
        """Share the current history with a target user by ID or email.

        ``user_email`` will be used to enter in the share form unless ``user_id``
        is also specified. The ``user_email`` however is always used to check
        the result if ``assert_valid`` is True.
        """
        self.navigate_to_history_share_page()
        self.components.histories.sharing.user_email_input.wait_for_and_send_keys(user_id or user_email)

        if screenshot:
            self.screenshot("history_sharing_user")
        self.components.histories.sharing.submit_sharing_with.wait_for_and_click()

        if assert_valid:
            self.assert_no_error_message()

            xpath = f'//td[contains(text(), "{user_email}")]'
            self.wait_for_xpath_visible(xpath)
