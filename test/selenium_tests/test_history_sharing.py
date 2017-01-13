from .framework import SeleniumTestCase
from .framework import selenium_test


class HistorySharingTestCase(SeleniumTestCase):

    @selenium_test
    def test_sharing_valid(self):
        user1_email, user2_email, history_id = self.setup_two_users_with_one_shared_history()
        self.submit_login(user2_email)
        response = self.api_get("histories/%s" % history_id, raw=True)
        assert response.status_code == 200

    @selenium_test
    def test_sharing_valid_by_id(self):
        user1_email, user2_email, history_id = self.setup_two_users_with_one_shared_history(share_by_id=True)
        self.submit_login(user2_email)
        response = self.api_get("histories/%s" % history_id, raw=True)
        assert response.status_code == 200

    @selenium_test
    def test_unsharing(self):
        user1_email, user2_email, history_id = self.setup_two_users_with_one_shared_history()
        self.submit_login(user1_email)
        self.navigate_to_history_share_page()

        with self.main_panel():
            first_user_element = self.wait_for_selector("#user-0-popup")
            first_user_element.click()

            unshare_link = self.wait_for_selector('a[href^="/history/sharing?unshare_user"]')
            unshare_link.click()

        self.navigate_to_history_share_page()
        with self.main_panel():
            self.assert_selector_absent("#user-0-popup")

        self.logout_if_needed()
        self.submit_login(user2_email)
        response = self.api_get("histories/%s" % history_id, raw=True)
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
        response = self.api_get("histories/%s" % history_id, raw=True)
        assert response.status_code == 403

    @selenium_test
    def test_sharing_with_invalid_user(self):
        user1_email = self._get_random_email()
        self.register(user1_email)
        self.share_history_with_user("invalid_user@test.com")
        self.assert_error_message(contains='is not a valid Galaxy user')

    @selenium_test
    def test_sharing_with_self(self):
        user1_email = self._get_random_email()
        self.register(user1_email)
        self.share_history_with_user(user1_email)
        self.assert_error_message(contains='You cannot send histories to yourself')

    def setup_two_users_with_one_shared_history(self, share_by_id=False):
        user1_email = self._get_random_email()
        user2_email = self._get_random_email()

        self.register(user1_email)
        self.logout_if_needed()
        self.register(user2_email)
        user2_id = self.api_get("users")[0]["id"]
        self.logout_if_needed()

        self.submit_login(user1_email)
        # Can't share an empty history...
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()

        history_id = self.current_history_id()
        if share_by_id:
            self.share_history_with_user(user2_email)
        else:
            self.share_history_with_user(user2_id)
        self.assert_no_error_message()
        self.logout_if_needed()

        return user1_email, user2_email, history_id

    def navigate_to_history_share_page(self):
        self.home()
        self.click_history_option("Share or Publish")

    def navigate_to_history_user_share_page(self):
        self.navigate_to_history_share_page()
        with self.main_panel():
            user_share_link_selector = 'a[href^="/history/share?"]'
            user_share_element = self.wait_for_selector(user_share_link_selector)
            user_share_element.click()

    def share_history_with_user(self, email):
        self.navigate_to_history_user_share_page()
        form_selector = "form#share"
        form = self.wait_for_selector(form_selector)
        # If expose_user_info is on would fill form out with this
        # line, in future dispatch on actual select2 div present or not.
        # self.select2_set_value(form_selector, email)
        self.fill(form, {"email": email})
        self.click_submit(form)
