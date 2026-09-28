import re

from playwright.sync_api import expect

from galaxy_test.base.api_util import random_name
from ..base.api_util import reset_password_link
from ..base.playwrightbrowser import Locators
from ..base.playwrighttestcase import PlaywrightTestCase

TEST_PASSWORD = "testpass"
RESET_PASSWORD = "resetpass"


class TestFrontendLogin(PlaywrightTestCase):
    def test_register(self):
        self.visit_url("/")
        page = self._page
        expect(page.locator(Locators.toolbar_login)).to_be_visible()
        page.click(Locators.toolbar_login)
        expect(page.locator(Locators.login_submit_button)).to_be_visible()
        expect(page.locator(Locators.register_link)).to_be_visible()
        page.click(Locators.register_link)
        user = random_name(prefix="shduser")
        self._submit_register_form(
            f"{user}@galaxyproject.org",
            TEST_PASSWORD,
            user,
        )
        expect(page.locator(Locators.login_submit_button)).to_be_visible()

    def test_create(self):
        user = random_name(prefix="shduser")
        self.create(
            email=f"{user}@galaxyproject.org",
            password=TEST_PASSWORD,
            username=user,
        )

    def test_logout(self):
        self._create_and_login()
        self._playwright_browser.expect_logged_in()
        self._playwright_browser.logout_if_logged_in()
        self._playwright_browser.expect_not_logged_in()

    def test_change_password(self):
        self._create_and_login()

    def test_forgot_password(self):
        user = random_name(prefix="shduser")
        email = f"{user}@galaxyproject.org"
        self.create(email=email, password=TEST_PASSWORD, username=user)
        self.visit_url("/login")
        page = self._page
        expect(page.locator(Locators.forgot_password_link)).to_be_visible()
        page.click(Locators.forgot_password_link)
        self._browser.fill_form_value("forgot_password", "email", email)
        self._browser.submit_form_with_name("forgot_password", "reset_password_button")
        expect(page.locator(Locators.reset_password_sent)).to_be_visible()

        self.visit_url(reset_password_link(email))
        expect(page).to_have_url(re.compile(r"/user/reset_password$"))
        self._browser.fill_form_value("reset_password", "password", RESET_PASSWORD)
        self._browser.fill_form_value("reset_password", "confirm", RESET_PASSWORD)
        self._browser.submit_form_with_name("reset_password", "set_password_button")
        self.check_page_for_string("Password successfully changed!")

        self.login(email, RESET_PASSWORD, username=user)
        self._playwright_browser.expect_logged_in()

    def _create_and_login(self):
        user = random_name(prefix="shduser")
        email = f"{user}@galaxyproject.org"
        self.create(
            email=email,
            password=TEST_PASSWORD,
            username=user,
        )
        self.login(email, TEST_PASSWORD, username=user)
