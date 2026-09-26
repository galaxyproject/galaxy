"""Browser availability checking utilities for Selenium and Playwright.

This module provides functions to check if browsers are available and properly
configured for automated testing. These functions are used for conditional test
skipping and diagnostic scripts.
"""

from functools import lru_cache

from playwright.sync_api import sync_playwright
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions

# Installation instruction constants
SELENIUM_INSTALL_INSTRUCTIONS = (
    "Install Chrome browser and chromedriver. See: https://chromedriver.chromium.org/getting-started"
)

PLAYWRIGHT_INSTALL_INSTRUCTIONS = "Install with: playwright install chromium"

# Skip message constants for pytest
SELENIUM_BROWSER_NOT_AVAILABLE_MESSAGE = f"Selenium Chrome browser not available. {SELENIUM_INSTALL_INSTRUCTIONS}"

PLAYWRIGHT_BROWSER_NOT_AVAILABLE_MESSAGE = (
    f"Playwright Chromium browser not available. {PLAYWRIGHT_INSTALL_INSTRUCTIONS}"
)


def is_selenium_browser_available() -> bool:
    """
    Check if Selenium WebDriver can launch Chrome browser.

    Returns:
        bool: True if Chrome browser is available and can be launched, False otherwise
    """
    try:
        options = ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)
        driver.quit()
        return True
    except Exception:
        return False


def is_playwright_browser_available() -> bool:
    """
    Check if Playwright Chromium browser is installed and available.

    Returns:
        bool: True if Playwright Chromium is installed, False otherwise
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


def get_selenium_availability_message() -> str:
    """
    Get a descriptive message about Selenium browser availability.

    Returns:
        str: Status message indicating if Selenium is available or how to enable it
    """
    if is_selenium_browser_available():
        return "Selenium Chrome browser is available"
    else:
        return SELENIUM_BROWSER_NOT_AVAILABLE_MESSAGE


def get_playwright_availability_message() -> str:
    """
    Get a descriptive message about Playwright browser availability.

    Returns:
        str: Status message indicating if Playwright is available or how to enable it
    """
    if is_playwright_browser_available():
        return "Playwright Chromium browser is available"
    else:
        return PLAYWRIGHT_BROWSER_NOT_AVAILABLE_MESSAGE


@lru_cache(maxsize=1)
def check_selenium_cached() -> bool:
    """
    Check Selenium browser availability with caching.

    This avoids repeatedly launching browsers during test collection.
    Uses lru_cache with maxsize=1 to cache the result of the check.

    Returns:
        bool: True if Selenium Chrome browser is available
    """
    return is_selenium_browser_available()


@lru_cache(maxsize=1)
def check_playwright_cached() -> bool:
    """
    Check Playwright browser availability with caching.

    This avoids repeatedly launching browsers during test collection.
    Uses lru_cache with maxsize=1 to cache the result of the check.

    Returns:
        bool: True if Playwright Chromium browser is available
    """
    return is_playwright_browser_available()


__all__ = (
    # Constants
    "SELENIUM_INSTALL_INSTRUCTIONS",
    "PLAYWRIGHT_INSTALL_INSTRUCTIONS",
    "SELENIUM_BROWSER_NOT_AVAILABLE_MESSAGE",
    "PLAYWRIGHT_BROWSER_NOT_AVAILABLE_MESSAGE",
    # Functions
    "is_selenium_browser_available",
    "is_playwright_browser_available",
    "get_selenium_availability_message",
    "get_playwright_availability_message",
    "check_selenium_cached",
    "check_playwright_cached",
)
