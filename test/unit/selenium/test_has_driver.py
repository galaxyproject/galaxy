"""Unit tests for galaxy.selenium.has_driver module."""

import pytest
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException as SeleniumTimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from galaxy.navigation.components import Target
from galaxy.selenium.has_driver import (
    HasDriver,
    exception_indicates_click_intercepted,
    exception_indicates_not_clickable,
    exception_indicates_stale_element,
)


class SimpleTarget(Target):
    """Simple concrete implementation of Target for testing."""

    def __init__(self, element_locator: tuple, description: str):
        """
        Initialize target with locator and description.

        Args:
            element_locator: Tuple of (By, locator_string) for Selenium
            description: Human-readable description
        """
        self._element_locator = element_locator
        self._description = description

    @property
    def description(self) -> str:
        """Return description."""
        return self._description

    @property
    def element_locator(self):
        """Return Selenium locator tuple."""
        return self._element_locator

    @property
    def component_locator(self):
        """Return component locator (not used in these tests)."""
        raise NotImplementedError("component_locator not needed for these tests")


class TestHasDriverImpl(HasDriver):
    """
    Concrete implementation of HasDriver for testing.

    HasDriver is an abstract mixin that requires a driver and timeout implementation.
    """

    def __init__(self, driver: WebDriver, default_timeout: float = 10.0):
        """
        Initialize test implementation.

        Args:
            driver: Selenium WebDriver instance
            default_timeout: Default timeout for waits
        """
        self.driver = driver
        self.default_timeout = default_timeout

    def timeout_for(self, **kwds) -> float:
        """Return timeout value (required abstract method)."""
        return kwds.get("timeout", self.default_timeout)


@pytest.fixture
def has_driver_instance(driver):
    """
    Create a HasDriver instance for testing.

    Args:
        driver: WebDriver fixture

    Returns:
        TestHasDriverImpl: Concrete HasDriver implementation
    """
    return TestHasDriverImpl(driver)


class TestElementFinding:
    """Tests for element finding methods."""

    def test_assert_xpath(self, has_driver_instance: TestHasDriverImpl, base_url: str) -> None:
        """Test finding element by XPath assertion."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        has_driver_instance.assert_xpath("//h1[@id='header']")

    def test_assert_xpath_fails_when_not_found(self, has_driver_instance: TestHasDriverImpl, base_url: str) -> None:
        """Test assert_xpath raises when element not found."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        with pytest.raises(NoSuchElementException):
            has_driver_instance.assert_xpath("//div[@id='nonexistent']")

    def test_assert_selector(self, has_driver_instance: TestHasDriverImpl, base_url: str) -> None:
        """Test finding element by CSS selector assertion."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        has_driver_instance.assert_selector("#test-div")

    def test_assert_selector_fails_when_not_found(self, has_driver_instance: TestHasDriverImpl, base_url: str) -> None:
        """Test assert_selector raises when element not found."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        with pytest.raises(NoSuchElementException):
            has_driver_instance.assert_selector("#nonexistent")

    def test_find_element_by_id(self, has_driver_instance: TestHasDriverImpl, base_url: str) -> None:
        """Test finding element by ID."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        element = has_driver_instance.find_element_by_id("test-div")
        assert element.text == "Test Div"

    def test_find_element_by_xpath(self, has_driver_instance: TestHasDriverImpl, base_url: str) -> None:
        """Test finding element by XPath."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        element = has_driver_instance.find_element_by_xpath("//p[@class='test-paragraph']")
        assert element.text == "Test Paragraph"

    def test_find_element_by_selector(self, has_driver_instance: TestHasDriverImpl, base_url: str) -> None:
        """Test finding element by CSS selector."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        element = has_driver_instance.find_element_by_selector("[data-testid='test-span']")
        assert element.text == "Test Span"

    def test_find_element_by_link_text(self, has_driver_instance: TestHasDriverImpl, base_url: str) -> None:
        """Test finding element by link text."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        element = has_driver_instance.find_element_by_link_text("Test Link")
        assert element.get_attribute("id") == "test-link"

    def test_find_elements_with_target(self, has_driver_instance: TestHasDriverImpl, base_url: str) -> None:
        """Test finding multiple elements using Target."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.CLASS_NAME, "item"), description="list items")
        elements = has_driver_instance.find_elements(target)
        assert len(elements) == 3


class TestVisibilityAndPresence:
    """Tests for visibility and presence checking methods."""

    def test_selector_is_displayed_visible_element(self, has_driver_instance, base_url):
        """Test checking if visible element is displayed."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        assert has_driver_instance.selector_is_displayed("#visible-element")

    def test_selector_is_displayed_hidden_element(self, has_driver_instance, base_url):
        """Test checking if hidden element is not displayed."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        assert not has_driver_instance.selector_is_displayed("#hidden-element")

    def test_is_displayed_with_target(self, has_driver_instance, base_url):
        """Test is_displayed with Target selector."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "visible-element"), description="visible element")
        assert has_driver_instance.is_displayed(target)

    def test_assert_selector_absent_or_hidden(self, has_driver_instance, base_url):
        """Test asserting element is absent or hidden."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        has_driver_instance.assert_selector_absent_or_hidden("#hidden-element")

    def test_assert_absent_or_hidden_with_target(self, has_driver_instance, base_url):
        """Test assert_absent_or_hidden with Target."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "hidden-element"), description="hidden element")
        has_driver_instance.assert_absent_or_hidden(target)

    def test_assert_selector_absent(self, has_driver_instance, base_url):
        """Test asserting element is completely absent from DOM."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        has_driver_instance.assert_selector_absent("#nonexistent-element")

    def test_assert_absent_with_target(self, has_driver_instance, base_url):
        """Test assert_absent with Target when element doesn't exist."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "nonexistent"), description="nonexistent element")
        has_driver_instance.assert_absent(target)

    def test_element_absent_returns_true(self, has_driver_instance, base_url):
        """Test element_absent returns True when element not in DOM."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "nonexistent"), description="nonexistent element")
        assert has_driver_instance.element_absent(target)

    def test_element_absent_returns_false(self, has_driver_instance, base_url):
        """Test element_absent returns False when element exists."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "test-div"), description="test div")
        assert not has_driver_instance.element_absent(target)

    def test_assert_disabled(self, has_driver_instance, base_url):
        """Test asserting element is disabled."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        target = SimpleTarget(
            element_locator=(By.ID, "disabled-button"), description="disabled button"
        )
        has_driver_instance.assert_disabled(target)


class TestWaitMethods:
    """Tests for wait methods."""

    def test_wait_for_xpath(self, has_driver_instance, base_url):
        """Test waiting for element by XPath."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        element = has_driver_instance.wait_for_xpath("//h1[@id='header']")
        assert element.text == "Test Page"

    def test_wait_for_xpath_visible(self, has_driver_instance, base_url):
        """Test waiting for visible element by XPath."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        element = has_driver_instance.wait_for_xpath_visible("//div[@id='visible-element']")
        assert element.is_displayed()

    def test_wait_for_selector(self, has_driver_instance, base_url):
        """Test waiting for element by CSS selector."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        element = has_driver_instance.wait_for_selector("#test-div")
        assert element.text == "Test Div"

    def test_wait_for_present_with_target(self, has_driver_instance, base_url):
        """Test wait_for_present with Target."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "test-div"), description="test div")
        element = has_driver_instance.wait_for_present(target)
        assert element is not None

    def test_wait_for_visible_with_target(self, has_driver_instance, base_url):
        """Test wait_for_visible with Target."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "visible-element"), description="visible element")
        element = has_driver_instance.wait_for_visible(target)
        assert element.is_displayed()

    def test_wait_for_selector_visible(self, has_driver_instance, base_url):
        """Test waiting for visible element by CSS selector."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        element = has_driver_instance.wait_for_selector_visible("#visible-element")
        assert element.is_displayed()

    def test_wait_for_selector_clickable(self, has_driver_instance, base_url):
        """Test waiting for clickable element by CSS selector."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        element = has_driver_instance.wait_for_selector_clickable("#clickable-button")
        assert element.is_enabled()

    def test_wait_for_clickable_with_target(self, has_driver_instance, base_url):
        """Test wait_for_clickable with Target."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        target = SimpleTarget(
            element_locator=(By.ID, "clickable-button"), description="clickable button"
        )
        element = has_driver_instance.wait_for_clickable(target)
        assert element.is_enabled()

    def test_wait_for_selector_absent(self, has_driver_instance, base_url):
        """Test waiting for element to be absent."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        # Element doesn't exist, so wait should succeed immediately
        has_driver_instance.wait_for_selector_absent("#nonexistent-element")

    def test_wait_for_absent_with_target(self, has_driver_instance, base_url):
        """Test wait_for_absent with Target."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "nonexistent"), description="nonexistent element")
        has_driver_instance.wait_for_absent(target)

    def test_wait_for_selector_absent_or_hidden(self, has_driver_instance, base_url):
        """Test waiting for element to be absent or hidden."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        has_driver_instance.wait_for_selector_absent_or_hidden("#hidden-element")

    def test_wait_for_absent_or_hidden_with_target(self, has_driver_instance, base_url):
        """Test wait_for_absent_or_hidden with Target."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "hidden-element"), description="hidden element")
        has_driver_instance.wait_for_absent_or_hidden(target)

    def test_wait_for_id(self, has_driver_instance, base_url):
        """Test waiting for element by ID."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        element = has_driver_instance.wait_for_id("test-div")
        assert element.get_attribute("id") == "test-div"

    def test_wait_for_element_count_of_at_least(self, has_driver_instance, base_url):
        """Test waiting for at least N elements."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.CLASS_NAME, "item"), description="list items")
        has_driver_instance.wait_for_element_count_of_at_least(target, 3)
        elements = has_driver_instance.find_elements(target)
        assert len(elements) >= 3

    def test_wait_timeout_with_custom_timeout(self, has_driver_instance, base_url):
        """Test that custom timeout is used."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        with pytest.raises(SeleniumTimeoutException):
            has_driver_instance.wait_for_selector("#nonexistent", timeout=1)

    def test_wait_for_delayed_element_becomes_visible(self, has_driver_instance, base_url):
        """Test waiting for element that becomes visible after delay."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        # Element becomes visible after 1 second
        element = has_driver_instance.wait_for_selector_visible("#delayed-element", timeout=3)
        assert element.is_displayed()


class TestClickAndInteraction:
    """Tests for click and interaction methods."""

    def test_click_xpath(self, has_driver_instance, base_url):
        """Test clicking element by XPath."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        has_driver_instance.click_xpath("//button[@id='clickable-button']")
        button = has_driver_instance.driver.find_element(By.ID, "clickable-button")
        assert button.text == "Clicked!"

    def test_click_selector(self, has_driver_instance, base_url):
        """Test clicking element by CSS selector."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        has_driver_instance.click_selector("#clickable-button")
        button = has_driver_instance.driver.find_element(By.ID, "clickable-button")
        assert button.text == "Clicked!"

    def test_click_label(self, has_driver_instance, base_url):
        """Test clicking link by text."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        has_driver_instance.click_label("Test Link")
        # Link was clicked (href="#" so stays on same page)

    def test_click_with_target(self, has_driver_instance, base_url):
        """Test click method with Target."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        target = SimpleTarget(
            element_locator=(By.ID, "clickable-button"), description="clickable button"
        )
        has_driver_instance.click(target)
        button = has_driver_instance.driver.find_element(By.ID, "clickable-button")
        assert button.text == "Clicked!"


class TestFormInteraction:
    """Tests for form interaction methods."""

    def test_fill_form(self, has_driver_instance, base_url):
        """Test filling form fields."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        form = has_driver_instance.driver.find_element(By.ID, "test-form")

        form_data = {"username": "testuser", "password": "testpass", "email": "test@example.com"}
        has_driver_instance.fill(form, form_data)

        # Verify fields were filled
        username = has_driver_instance.driver.find_element(By.ID, "username")
        assert username.get_attribute("value") == "testuser"

        password = has_driver_instance.driver.find_element(By.ID, "password")
        assert password.get_attribute("value") == "testpass"

        email = has_driver_instance.driver.find_element(By.ID, "email")
        assert email.get_attribute("value") == "test@example.com"

    def test_click_submit(self, has_driver_instance, base_url):
        """Test clicking submit button on form."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        form = has_driver_instance.driver.find_element(By.ID, "test-form")
        has_driver_instance.click_submit(form)

        # Verify form was submitted (result div appears)
        result = has_driver_instance.wait_for_id("form-result", timeout=2)
        assert result.text == "Form submitted!"


class TestActionChainsAndKeys:
    """Tests for action chains and key sending methods."""

    def test_action_chains(self, has_driver_instance, base_url):
        """Test creating action chains."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        chains = has_driver_instance.action_chains()
        assert chains is not None

    def test_send_enter(self, has_driver_instance, base_url):
        """Test sending ENTER key."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        element = has_driver_instance.driver.find_element(By.ID, "username")
        element.click()
        has_driver_instance.send_enter(element)
        # Key was sent (no exception)

    def test_send_escape(self, has_driver_instance, base_url):
        """Test sending ESCAPE key."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        element = has_driver_instance.driver.find_element(By.ID, "username")
        element.click()
        has_driver_instance.send_escape(element)
        # Key was sent (no exception)

    def test_send_backspace(self, has_driver_instance, base_url):
        """Test sending BACKSPACE key."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        element = has_driver_instance.driver.find_element(By.ID, "username")
        element.send_keys("test")
        has_driver_instance.send_backspace(element)
        # Verify one character was deleted
        assert element.get_attribute("value") == "tes"


class TestFrameSwitching:
    """Tests for frame switching functionality."""

    def test_switch_to_frame(self, has_driver_instance, base_url):
        """Test switching to iframe."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        has_driver_instance.switch_to_frame("frame")

        # Verify we're in the frame by finding frame-specific element
        frame_header = has_driver_instance.driver.find_element(By.ID, "frame-header")
        assert frame_header.text == "Inside Frame"

        # Switch back
        has_driver_instance.driver.switch_to.default_content()


class TestAlertHandling:
    """Tests for alert handling."""

    def test_accept_alert(self, has_driver_instance, base_url):
        """Test accepting browser alert."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        has_driver_instance.click_selector("#alert-button")

        # Accept the alert
        has_driver_instance.accept_alert()

        # Verify we're back on the main page
        header = has_driver_instance.driver.find_element(By.ID, "header")
        assert header.text == "Test Page"


class TestUtilityMethods:
    """Tests for utility methods."""

    def test_navigate_to(self, has_driver_instance: TestHasDriverImpl, base_url: str) -> None:
        """Test navigating to a URL and changing pages."""
        # Navigate to first page
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        assert "basic.html" in has_driver_instance.driver.current_url
        # Verify first page loaded by checking for expected element
        header = has_driver_instance.driver.find_element(By.ID, "header")
        assert header.text == "Test Page"

        # Navigate to second page
        has_driver_instance.navigate_to(f"{base_url}/frame.html")
        assert "frame.html" in has_driver_instance.driver.current_url
        # Verify we actually navigated to a different page
        frame_header = has_driver_instance.driver.find_element(By.ID, "frame-header")
        assert frame_header.text == "Inside Frame"

        # Verify the original element is no longer present
        assert len(has_driver_instance.driver.find_elements(By.ID, "header")) == 0

    def test_re_get_with_query_params_adds_question_mark(
        self, has_driver_instance, base_url
    ):
        """Test adding query params to URL without existing params."""
        has_driver_instance.driver.get(f"{base_url}/basic.html")
        has_driver_instance.re_get_with_query_params("foo=bar")
        assert "?foo=bar" in has_driver_instance.driver.current_url

    def test_re_get_with_query_params_appends_to_existing(
        self, has_driver_instance, base_url
    ):
        """Test adding query params to URL with existing params."""
        has_driver_instance.driver.get(f"{base_url}/basic.html?existing=param")
        has_driver_instance.re_get_with_query_params("foo=bar")
        current_url = has_driver_instance.driver.current_url
        assert "existing=param" in current_url
        assert "foo=bar" in current_url

    def test_prepend_timeout_message(self, has_driver_instance):
        """Test prepending message to timeout exception."""
        original = SeleniumTimeoutException(msg="original message")
        new_exception = has_driver_instance.prepend_timeout_message(
            original, "New prefix:"
        )
        assert "New prefix:" in new_exception.msg
        assert "original message" in new_exception.msg


class TestExceptionHelpers:
    """Tests for exception helper functions."""

    def test_exception_indicates_click_intercepted(self):
        """Test detecting click intercepted exceptions."""
        exc = Exception("Element click intercepted")
        assert exception_indicates_click_intercepted(exc)

        exc = Exception("Something else")
        assert not exception_indicates_click_intercepted(exc)

    def test_exception_indicates_not_clickable(self):
        """Test detecting not clickable exceptions."""
        exc = Exception("Element is not clickable")
        assert exception_indicates_not_clickable(exc)

        exc = Exception("Something else")
        assert not exception_indicates_not_clickable(exc)

    def test_exception_indicates_stale_element(self):
        """Test detecting stale element exceptions."""
        exc = Exception("stale element reference")
        assert exception_indicates_stale_element(exc)

        exc = Exception("Something else")
        assert not exception_indicates_stale_element(exc)
