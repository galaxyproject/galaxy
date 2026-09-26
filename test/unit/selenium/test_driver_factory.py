"""Unit tests for driver_factory.py - ConfiguredDriver with both Selenium and Playwright backends."""

from typing import get_args

import pytest

from galaxy.selenium.driver_factory import (
    ConfiguredDriver,
    get_playwright_browser_type,
    PLAYWRIGHT_REMOTE_UNSUPPORTED_MESSAGE,
    PlaywrightBrowserName,
)
from galaxy.selenium.has_driver_protocol import fixed_timeout_handler
from .util import (
    skip_unless_playwright_browser_cached,
    skip_unless_selenium_browser_cached,
)

# Get the valid Playwright browser names from the Literal type
VALID_PLAYWRIGHT_BROWSERS = get_args(PlaywrightBrowserName)


def configured_driver(**kwds) -> ConfiguredDriver:
    """Return a basic ConfiguredDriver for testing."""
    return ConfiguredDriver(fixed_timeout_handler(5.0), **kwds)


class TestGetPlaywrightBrowserType:
    """Test browser name mapping for Playwright."""

    def test_auto_maps_to_chromium(self):
        result = get_playwright_browser_type("auto")
        assert result == "chromium"
        assert result in VALID_PLAYWRIGHT_BROWSERS

    def test_chrome_maps_to_chromium(self):
        result = get_playwright_browser_type("CHROME")
        assert result == "chromium"
        assert result in VALID_PLAYWRIGHT_BROWSERS

    def test_firefox_maps_to_firefox(self):
        result = get_playwright_browser_type("FIREFOX")
        assert result == "firefox"
        assert result in VALID_PLAYWRIGHT_BROWSERS

    def test_edge_raises_not_implemented(self):
        """EDGE should raise NotImplementedError with helpful message."""
        with pytest.raises(NotImplementedError) as exc_info:
            get_playwright_browser_type("EDGE")
        error_msg = str(exc_info.value)
        assert "does not have a direct Playwright mapping" in error_msg
        assert "use 'CHROME' or 'auto' instead" in error_msg

    def test_safari_raises_not_implemented(self):
        """SAFARI should raise NotImplementedError with helpful message."""
        with pytest.raises(NotImplementedError) as exc_info:
            get_playwright_browser_type("SAFARI")
        error_msg = str(exc_info.value)
        assert "does not have a direct Playwright mapping" in error_msg
        assert "webkit" in error_msg.lower()
        assert "Selenium backend" in error_msg

    def test_unknown_browser_raises_not_implemented(self):
        """Unknown browser types should raise NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            get_playwright_browser_type("OPERA")
        error_msg = str(exc_info.value)
        assert "not supported with Playwright backend" in error_msg
        assert "CHROME, FIREFOX, auto" in error_msg

    def test_return_type_is_valid_playwright_browser(self):
        """All successful return values should be valid PlaywrightBrowserName literals."""
        test_browsers = ["auto", "CHROME", "FIREFOX"]
        for browser in test_browsers:
            result = get_playwright_browser_type(browser)
            assert result in VALID_PLAYWRIGHT_BROWSERS, f"Browser '{browser}' mapped to invalid type '{result}'"


@skip_unless_selenium_browser_cached()
class TestConfiguredDriverSelenium:
    """Test ConfiguredDriver with Selenium backend."""

    def test_default_backend_is_selenium(self):
        """Default backend_type should be 'selenium' for backward compatibility."""
        driver = configured_driver(headless=True)
        try:
            assert driver.backend_type == "selenium"
            assert driver.driver_impl.backend_type == "selenium"
        finally:
            driver.quit()

    def test_explicit_selenium_backend(self):
        """Explicitly requesting selenium backend should work."""
        driver = configured_driver(backend_type="selenium", headless=True)
        try:
            assert driver.backend_type == "selenium"
            assert driver.driver_impl.backend_type == "selenium"
        finally:
            driver.quit()

    def test_driver_impl_has_protocol_methods(self):
        """Driver impl should implement HasDriverProtocol methods."""
        driver = configured_driver(headless=True)
        try:
            assert hasattr(driver.driver_impl, "navigate_to")
            assert hasattr(driver.driver_impl, "find_element_by_id")
            assert hasattr(driver.driver_impl, "wait_for_selector")
            assert hasattr(driver.driver_impl, "click_xpath")
        finally:
            driver.quit()

    # Make a test like this work based on checking for geckodriver or chromedriver in PATH.
    # def test_serialization_preserves_backend(self):
    #     """Serialization should preserve backend_type."""
    #     driver = configured_driver(backend_type="selenium", headless=True, browser="FIREFOX")
    #     try:
    #         config = driver.to_dict()
    #         assert config["backend_type"] == "selenium"
    #         assert config["browser"] == "FIREFOX"
    #         assert config["headless"] is True
    #     finally:
    #         driver.quit()

    def test_deserialization_restores_backend(self):
        """Deserialization should restore correct backend."""
        config = {
            "browser": "CHROME",
            "remote": False,
            "remote_host": "127.0.0.1",
            "remote_port": "4444",
            "headless": True,
            "backend_type": "selenium",
        }
        driver = ConfiguredDriver.from_dict(fixed_timeout_handler(5.0), config)
        try:
            assert driver.backend_type == "selenium"
        finally:
            driver.quit()


class TestConfiguredDriverPlaywright:
    """Test ConfiguredDriver with Playwright backend."""

    @skip_unless_playwright_browser_cached()
    def test_playwright_backend_creation(self):
        """Should be able to create Playwright backend."""
        driver = configured_driver(backend_type="playwright", headless=True)
        try:
            assert driver.backend_type == "playwright"
            assert driver.driver_impl.backend_type == "playwright"
        finally:
            driver.quit()

    @skip_unless_playwright_browser_cached()
    def test_playwright_firefox_browser(self):
        """Should support Firefox browser with Playwright."""
        driver = configured_driver(backend_type="playwright", browser="FIREFOX", headless=True)
        try:
            assert driver.backend_type == "playwright"
            assert driver.config["browser"] == "FIREFOX"
        finally:
            driver.quit()

    @skip_unless_playwright_browser_cached()
    def test_playwright_driver_impl_has_protocol_methods(self):
        """Playwright driver impl should implement HasDriverProtocol methods."""
        driver = configured_driver(backend_type="playwright", headless=True)
        try:
            assert hasattr(driver.driver_impl, "navigate_to")
            assert hasattr(driver.driver_impl, "find_element_by_id")
            assert hasattr(driver.driver_impl, "wait_for_selector")
            assert hasattr(driver.driver_impl, "click_xpath")
        finally:
            driver.quit()

    @skip_unless_playwright_browser_cached()
    def test_playwright_serialization(self):
        """Playwright config should serialize correctly."""
        driver = configured_driver(backend_type="playwright", headless=True, browser="FIREFOX")
        try:
            config = driver.to_dict()
            assert config["backend_type"] == "playwright"
            assert config["browser"] == "FIREFOX"
        finally:
            driver.quit()

    def test_playwright_remote_raises_exception(self):
        """Playwright should raise exception when remote=True.

        Note: This test doesn't require a browser to be installed since it only
        tests validation logic - the exception is raised before any browser is launched.
        """
        with pytest.raises(Exception) as exc_info:
            configured_driver(backend_type="playwright", remote=True)
        assert PLAYWRIGHT_REMOTE_UNSUPPORTED_MESSAGE in str(exc_info.value)

    @skip_unless_playwright_browser_cached()
    def test_playwright_has_page_attribute(self):
        """Playwright driver impl should have page attribute."""
        driver = configured_driver(backend_type="playwright", headless=True)
        try:
            assert hasattr(driver.driver_impl, "page")
        finally:
            driver.quit()


class TestConfiguredDriverValidation:
    """Test ConfiguredDriver validation and error handling."""

    def test_invalid_backend_type_raises_error(self):
        """Invalid backend_type should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            configured_driver(backend_type="invalid")
        assert "Invalid backend_type" in str(exc_info.value)

    def test_playwright_remote_validation(self):
        """Playwright + remote should fail with clear message."""
        with pytest.raises(Exception) as exc_info:
            configured_driver(backend_type="playwright", remote=True, headless=True)
        error_msg = str(exc_info.value)
        assert "does not support remote" in error_msg
        assert "Selenium Grid" in error_msg
