"""Pytest configuration and fixtures for selenium unit tests."""

import pytest
from playwright.sync_api import sync_playwright
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

from .test_server import TestHTTPServer


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
def playwright_browser():
    """
    Create a Playwright browser instance for each test.

    Yields:
        Browser: Playwright Browser instance
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def playwright_page(playwright_browser):
    """
    Create a Playwright page instance for each test.

    Args:
        playwright_browser: Playwright browser fixture

    Yields:
        Page: Playwright Page instance
    """
    page = playwright_browser.new_page()
    yield page
    page.close()
