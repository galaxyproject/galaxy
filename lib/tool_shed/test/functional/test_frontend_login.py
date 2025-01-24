from playwright.sync_api import (
    expect,
    Page,
)

from galaxy_test.base.api_util import random_name
from ..base.api import skip_if_api_v1
from ..base.playwrightbrowser import (
    Locators,
    PlaywrightShedBrowser,
)
from ..base.twilltestcase import ShedTwillTestCase


class PlaywrightTestCase(ShedTwillTestCase):
    @property
    def _playwright_browser(self) -> PlaywrightShedBrowser:
        browser = self._browser
        assert isinstance(browser, PlaywrightShedBrowser)
        return browser

    @property
    def _page(self) -> Page:
        return self._playwright_browser._page


TEST_PASSWORD = "testpass"


class TestFrontendLogin(PlaywrightTestCase):
    @skip_if_api_v1
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

    @skip_if_api_v1
    def test_create(self):
        user = random_name(prefix="shduser")
        self.create(
            email=f"{user}@galaxyproject.org",
            password=TEST_PASSWORD,
            username=user,
        )

    @skip_if_api_v1
    def test_logout(self):
        self._create_and_login()
        self._playwright_browser.expect_logged_in()
        self._playwright_browser.logout_if_logged_in()
        self._playwright_browser.expect_not_logged_in()

    @skip_if_api_v1
    def test_change_password(self):
        self._create_and_login()

    def _create_and_login(self):
        user = random_name(prefix="shduser")
        email = f"{user}@galaxyproject.org"
        self.create(
            email=email,
            password=TEST_PASSWORD,
            username=user,
        )
        self.login(email, TEST_PASSWORD, username=user)
