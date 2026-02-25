from collections.abc import Generator

import pytest
from playwright.sync_api import Browser

from ..base.browser import ShedBrowser
from ..base.playwrightbrowser import PlaywrightShedBrowser


def playwright_browser(browser: Browser) -> Generator[ShedBrowser, None, None]:
    page = browser.new_page()
    yield PlaywrightShedBrowser(page)


shed_browser = pytest.fixture(scope="class")(playwright_browser)
