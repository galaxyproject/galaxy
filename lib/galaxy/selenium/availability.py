"""Browser availability checking utilities for Selenium and Playwright.

This module provides functions to check if browsers are available and properly
configured for automated testing. These functions are used for conditional test
skipping and diagnostic scripts.
"""

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
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options as ChromeOptions

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
        from playwright.sync_api import sync_playwright

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


class BrowserAvailability:
    """Cached browser availability checker to avoid repeated browser launches."""

    def __init__(self):
        """Initialize with no cached values."""
        self._selenium_available = None
        self._playwright_available = None

    def check_selenium(self) -> bool:
        """
        Check Selenium browser availability with caching.

        Returns:
            bool: True if Selenium Chrome browser is available
        """
        if self._selenium_available is None:
            self._selenium_available = is_selenium_browser_available()
        return self._selenium_available

    def check_playwright(self) -> bool:
        """
        Check Playwright browser availability with caching.

        Returns:
            bool: True if Playwright Chromium browser is available
        """
        if self._playwright_available is None:
            self._playwright_available = is_playwright_browser_available()
        return self._playwright_available

    def reset_cache(self):
        """Reset the cached availability checks."""
        self._selenium_available = None
        self._playwright_available = None


# Global instance for caching browser availability across test collection
_global_availability_cache = BrowserAvailability()


def check_selenium_cached() -> bool:
    """
    Check Selenium browser availability using global cache.

    This avoids repeatedly launching browsers during test collection.

    Returns:
        bool: True if Selenium Chrome browser is available
    """
    return _global_availability_cache.check_selenium()


def check_playwright_cached() -> bool:
    """
    Check Playwright browser availability using global cache.

    This avoids repeatedly launching browsers during test collection.

    Returns:
        bool: True if Playwright Chromium browser is available
    """
    return _global_availability_cache.check_playwright()


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
    # Classes
    "BrowserAvailability",
)
