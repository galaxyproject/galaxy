from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class TestLogin(SeleniumTestCase):
    @selenium_test
    def test_login_accessibility(self):
        self.home()
        self.components.masthead.login_masthead_button.wait_for_and_click()
        login = self.components.login
        login.form.assert_no_axe_violations_with_impact_of_at_least("moderate")

    @selenium_test
    def test_reset_password_link(self):
        email = self._get_random_email()
        self.home()
        self.components.masthead.login_masthead_button.wait_for_and_click()
        login = self.components.login
        self.fill(login.form.wait_for_visible(), {"login": email})
        login.reset_password_link.wait_for_and_click()
        reset_password = self.components.reset_password
        assert reset_password.email.wait_for_visible().get_attribute("value") == email
        reset_password.submit.wait_for_and_click()
        # Test servers usually lack SMTP, so either response proves the request round-tripped.
        alert_text = reset_password.alert.wait_for_visible().text
        assert "confirmation email" in alert_text or "Mail is not configured" in alert_text

    @selenium_test
    def test_reset_password_direct_load(self):
        self.get("login/reset_password")
        self.components.reset_password.email.wait_for_visible()

    @selenium_test
    def test_logging_in(self):
        email = self._get_random_email()
        self.register(email)
        self.logout_if_needed()
        self.home()
        self.submit_login(email, assert_valid=True)
        self.assert_no_error_message()
        assert self.is_logged_in()

    @selenium_test
    def test_invalid_logins(self):
        bad_emails = ["test2@test.org", "test", "'; SELECT * FROM galaxy_user WHERE 'u' = 'u';"]
        for bad_email in bad_emails:
            self.home()
            self.submit_login(bad_email, assert_valid=False)
            self.assert_error_message()

    @selenium_test
    def test_invalid_passwords(self):
        bad_passwords = ["1234", "; SELECT * FROM galaxy_user"]
        for bad_password in bad_passwords:
            self.home()
            self.submit_login(self._get_random_email(), password=bad_password, assert_valid=False)
            self.assert_error_message()

    @selenium_test
    def test_wrong_password(self):
        email = self._get_random_email()
        self.register(email)
        self.logout_if_needed()
        self.home()
        self.submit_login(email, password="12345678", assert_valid=False)
        self.assert_error_message()
