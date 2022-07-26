from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class RegistrationTestCase(SeleniumTestCase):
    @selenium_test
    def test_landing(self):
        # loading galaxy homepage
        self.home()
        assert self.driver.title == "Galaxy", self.driver.title
        self.components.masthead._.wait_for_visible()

    @selenium_test
    def test_registration(self):
        self.home()
        self.register()

    @selenium_test
    def test_logout(self):
        self.home()
        self.register()
        assert self.is_logged_in()
        self.logout_if_needed()
        assert not self.is_logged_in()
        self.home()
        self.components.masthead.username.assert_absent_or_hidden()

    @selenium_test
    def test_reregister_email_fails(self):
        self.home()
        email = self._get_random_email()
        password = self.default_password
        confirm = password
        username = email.split("@")[0]
        self.register(email, password, username, confirm)
        self.logout_if_needed()
        self.register(email, password, username, confirm, assert_valid=False)
        self.assert_error_message()

    @selenium_test
    def test_reregister_username_fails(self):
        self.home()
        email1 = self._get_random_email()
        email2 = self._get_random_email()
        password = self.default_password
        confirm = password
        username = email1.split("@")[0]
        self.register(email1, password, username, confirm)
        self.logout_if_needed()
        self.register(email2, password, username, confirm, assert_valid=False)
        self.assert_error_message(contains="Public name is taken")

    @selenium_test
    def test_bad_emails(self):
        bad_emails = ["bob", "bob@", "bob.cantmakeme"]
        good_email = self._get_random_email()
        password = self.default_password
        confirm = password
        username = good_email.split("@")[0]
        for bad_email in bad_emails:
            self.register(bad_email, password, username, confirm, assert_valid=False)
            self.assert_error_message(contains="The format of the email address is not correct.")

    @selenium_test
    def test_short_password(self):
        self.register(password="1234", assert_valid=False)
        self.assert_error_message(contains="Use a password of at least 6 characters")

    @selenium_test
    def test_password_confirmation(self):
        bad_confirms = ["1234", "12345678", "123456 7"]
        for bad_confirm in bad_confirms:
            self.register(confirm=bad_confirm, assert_valid=False)
            self.assert_error_message(contains="Passwords do not match")

    @selenium_test
    def test_bad_usernames(self):
        bad_usernames = ["BOBERT", "Robert Paulson", "bobert!"]
        for bad_username in bad_usernames:
            self.register(username=bad_username, assert_valid=False)
            self.assert_error_message(contains="Public name must contain only ")
