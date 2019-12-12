from .framework import (
    selenium_test,
    SeleniumTestCase
)


class LoginTestCase(SeleniumTestCase):

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
        bad_emails = ['test2@test.org', 'test', '', "'; SELECT * FROM galaxy_user WHERE 'u' = 'u';"]
        for bad_email in bad_emails:
            self.home()
            self.submit_login(bad_email, assert_valid=False)
            self.assert_error_message()

    @selenium_test
    def test_invalid_passwords(self):
        bad_passwords = ['1234', '', '; SELECT * FROM galaxy_user']
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
