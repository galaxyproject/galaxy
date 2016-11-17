import random
import string

from .framework import SeleniumTestCase
from .framework import selenium_test

DEFAULT_PASSWORD = '123456'


class RegistrationTestCase(SeleniumTestCase):

    @selenium_test
    def test_landing(self):
        # loading galaxy homepage
        self.home()
        assert self.driver.title == "Galaxy", self.driver.title
        self.assert_xpath("//div[@id='masthead']")

    @selenium_test
    def test_registration(self):
        self.home()
        self._register()

    @selenium_test
    def test_logout(self):
        self.home()
        self._register()
        assert self.is_logged_in()
        self.logout_if_needed()
        assert not self.is_logged_in()
        self.home()
        assert len(self.driver.find_elements_by_xpath(self.test_data["selectors"]["masthead"]["userMenu"]["userEmail_xpath"])) == 0

    @selenium_test
    def test_reregister_email_fails(self):
        self.home()
        email = self._get_random_email()
        password = DEFAULT_PASSWORD
        confirm = password
        username = email.split("@")[0]
        self._register(email, password, username, confirm)
        self.logout_if_needed()
        self._register(email, password, username, confirm, assert_valid=False)
        self.assert_selector(self.test_data["selectors"]["messages"]["error"])

    @selenium_test
    def test_reregister_username_fails(self):
        self.home()
        email1 = self._get_random_email()
        email2 = self._get_random_email()
        password = DEFAULT_PASSWORD
        confirm = password
        username = email1.split("@")[0]
        self._register(email1, password, username, confirm)
        self.logout_if_needed()
        self._register(email2, password, username, confirm, assert_valid=False)
        error_element = self.driver.find_element_by_css_selector(self.test_data["selectors"]["messages"]["error"])
        assert error_element
        assert 'Public name is taken; please choose another' in error_element.text, error_element.text

    @selenium_test
    def test_bad_emails(self):
        bad_emails = [ 'bob', 'bob@', 'bob@idontwanttocleanup', 'bob.cantmakeme' ]
        good_email = self._get_random_email()
        password = DEFAULT_PASSWORD
        confirm = password
        username = good_email.split("@")[0]

        for bad_email in bad_emails:
            self._register(bad_email, password, username, confirm, assert_valid=False)
            error_element = self.driver.find_element_by_css_selector(self.test_data["selectors"]["messages"]["error"])
            assert error_element
            assert 'The format of the email address is not correct.' in error_element.text, error_element.text

    @selenium_test
    def test_short_password(self):
        self._register(password="1234", assert_valid=False)
        error_element = self.driver.find_element_by_css_selector(self.test_data["selectors"]["messages"]["error"])
        assert error_element
        assert 'Use a password of at least 6 characters' in error_element.text, error_element.text

    @selenium_test
    def test_password_confirmation(self):
        bad_confirms = ['1234', '12345678', '123456 7', '']
        for bad_confirm in bad_confirms:
            self._register(confirm=bad_confirm, assert_valid=False)
            error_element = self.driver.find_element_by_css_selector(self.test_data["selectors"]["messages"]["error"])
            assert error_element
            assert 'Passwords don\'t match' in error_element.text, error_element.text

    @selenium_test
    def test_bad_usernames(self):
        bad_usernames = ['BOBERT', 'Robert Paulson', 'bobert!']
        for bad_username in bad_usernames:
            self._register(username=bad_username, assert_valid=False)
            error_element = self.driver.find_element_by_css_selector(self.test_data["selectors"]["messages"]["error"])
            assert error_element
            assert 'Public name must contain only ' in error_element.text, error_element.text

    def _get_random_email(self, username=None, domain=None):
        username = username or 'test'
        domain = domain or 'test.test'
        suffix = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))
        return username + suffix + '@' + domain

    def _register(self, email=None, password=None, username=None, confirm=None, assert_valid=True):
        if email is None:
            email = self._get_random_email()
        if password is None:
            password = DEFAULT_PASSWORD
        if confirm is None:
            confirm = password
        if username is None:
            username = email.split("@")[0]

        self.home()
        self.click_masthead_user()
        self.click_label(self.test_data["labels"]["masthead"]["userMenu"]["register"])
        with self.main_panel():
            register_form_id = self.test_data["selectors"]["registrationPage"]["form"]
            form = self.wait_for_id(register_form_id)
            self.fill(form, dict(
                email=email,
                password=password,
                username=username,
                confirm=confirm
            ))
            self.click_xpath(self.test_data["selectors"]["registrationPage"]["submit_xpath"])
        if assert_valid:
            self.home()
            self.click_masthead_user()
            text = self.driver.find_element_by_xpath(self.test_data["selectors"]["masthead"]["userMenu"]["userEmail_xpath"]).text
            assert email in text
            assert self.get_logged_in_user()["email"] == email
