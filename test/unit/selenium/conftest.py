"""Pytest configuration and fixtures for selenium unit tests."""

from typing import cast

import pytest
from playwright.sync_api import sync_playwright
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions

from galaxy.selenium.availability import (
    PLAYWRIGHT_BROWSER_NOT_AVAILABLE_MESSAGE,
    SELENIUM_BROWSER_NOT_AVAILABLE_MESSAGE,
)
from galaxy.selenium.has_driver_protocol import HasDriverProtocol
from galaxy.selenium.has_driver_proxy import HasDriverProxyImpl
from galaxy.selenium.has_playwright_driver import PlaywrightResources
from galaxy.selenium.navigates_galaxy import (
    NavigatesGalaxy,
    WaitType,
)
from .test_has_driver import (
    TestHasDriverImpl,
    TestHasPlaywrightDriverImpl,
)
from .test_server import TestHTTPServer
from .util import (
    check_playwright_cached,
    check_selenium_cached,
)


@pytest.fixture(scope="session")
def test_server():
    """
    Create and start a test HTTP server for the entire test session.

    Yields:
        TestHTTPServer: Running HTTP server instance
    """
    server = TestHTTPServer(port=0)  # Use random available port
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="function")
def chrome_options():
    """
    Create Chrome options for headless testing.

    Returns:
        ChromeOptions: Configured Chrome options
    """
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    return options


@pytest.fixture(scope="function")
def driver(chrome_options):
    """
    Create a WebDriver instance for each test.

    Args:
        chrome_options: Chrome options fixture

    Yields:
        WebDriver: Chrome WebDriver instance
    """
    if not check_selenium_cached():
        pytest.skip(SELENIUM_BROWSER_NOT_AVAILABLE_MESSAGE)

    _driver = webdriver.Chrome(options=chrome_options)
    _driver.implicitly_wait(0)  # Disable implicit waits, use explicit waits in tests
    yield _driver
    _driver.quit()


@pytest.fixture(scope="session")
def base_url(test_server):
    """
    Get the base URL for the test server.

    Args:
        test_server: Test HTTP server fixture

    Returns:
        str: Base URL of the test server
    """
    return test_server.get_url()


@pytest.fixture(scope="function")
def playwright_resources():
    """
    Create Playwright resources (playwright, browser, page) for each test.

    Yields:
        PlaywrightResources: NamedTuple containing playwright, browser, and page instances
    """
    if not check_playwright_cached():
        pytest.skip(PLAYWRIGHT_BROWSER_NOT_AVAILABLE_MESSAGE)

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    yield PlaywrightResources(playwright=playwright, browser=browser, page=page)

    # Cleanup in reverse order
    page.close()
    browser.close()
    playwright.stop()


class FixturePage(HasDriverProxyImpl[WaitType], NavigatesGalaxy):
    """``NavigatesGalaxy`` helpers driving a static fixture page instead of a Galaxy server."""

    def build_url(self, url: str, for_selenium: bool = True) -> str:
        raise NotImplementedError("fixture pages have no Galaxy to build URLs for")

    def screenshot(self, label: str) -> None:
        pass

    def sleep_for(self, wait_type: WaitType) -> None:
        # Fixture pages render synchronously, and the test driver's fixed timeout would sleep 10s per wait.
        pass


@pytest.fixture(params=["selenium", "playwright"])
def fixture_page(request, base_url):
    """Open a page from ``fixtures/`` with ``NavigatesGalaxy`` helpers, once per browser backend."""
    impl: HasDriverProtocol
    if request.param == "selenium":
        impl = cast(HasDriverProtocol, TestHasDriverImpl(request.getfixturevalue("driver")))
    else:
        impl = cast(HasDriverProtocol, TestHasPlaywrightDriverImpl(request.getfixturevalue("playwright_resources")))
    page = FixturePage(impl)

    def open_page(name: str) -> FixturePage:
        page.navigate_to(f"{base_url}/{name}")
        return page

    return open_page
