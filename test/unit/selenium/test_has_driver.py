"""Unit tests for galaxy.selenium.has_driver module."""

from typing import cast

import pytest
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException as SeleniumTimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from galaxy.navigation.components import Target
from galaxy.selenium.availability import (
    PLAYWRIGHT_BROWSER_NOT_AVAILABLE_MESSAGE,
    SELENIUM_BROWSER_NOT_AVAILABLE_MESSAGE,
)
from galaxy.selenium.has_driver import (
    exception_indicates_click_intercepted,
    exception_indicates_not_clickable,
    exception_indicates_stale_element,
    HasDriver,
)
from galaxy.selenium.has_driver_protocol import (
    fixed_timeout_handler,
    HasDriverProtocol,
    TimeoutCallback,
)
from galaxy.selenium.has_driver_proxy import HasDriverProxyImpl
from galaxy.selenium.has_playwright_driver import (
    HasPlaywrightDriver,
    PlaywrightResources,
    PlaywrightTimeoutException,
)
from .util import (
    check_playwright_cached,
    check_selenium_cached,
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

    @property
    def timeout_handler(self) -> TimeoutCallback:
        """Return timeout value."""
        return fixed_timeout_handler(self.default_timeout)


class TestHasPlaywrightDriverImpl(HasPlaywrightDriver):
    """
    Concrete implementation of HasPlaywrightDriver for testing.

    HasPlaywrightDriver is an abstract mixin that requires PlaywrightResources and timeout implementation.
    """

    def __init__(self, playwright_resources: PlaywrightResources, default_timeout: float = 10.0):
        """
        Initialize test implementation.

        Args:
            playwright_resources: PlaywrightResources containing playwright, browser, and page
            default_timeout: Default timeout for waits
        """
        self._playwright_resources = playwright_resources
        self.default_timeout = default_timeout
        self._current_frame = None

    @property
    def timeout_handler(self) -> TimeoutCallback:
        """Return timeout value."""
        return fixed_timeout_handler(self.default_timeout)


@pytest.fixture(
    params=[
        pytest.param(
            "selenium",
            marks=pytest.mark.skipif(
                not check_selenium_cached(),
                reason=SELENIUM_BROWSER_NOT_AVAILABLE_MESSAGE,
            ),
        ),
        pytest.param(
            "playwright",
            marks=pytest.mark.skipif(
                not check_playwright_cached(),
                reason=PLAYWRIGHT_BROWSER_NOT_AVAILABLE_MESSAGE,
            ),
        ),
        pytest.param(
            "proxy-selenium",
            marks=pytest.mark.skipif(
                not check_selenium_cached(),
                reason=SELENIUM_BROWSER_NOT_AVAILABLE_MESSAGE,
            ),
        ),
    ]
)
def has_driver_instance(request, driver, playwright_resources) -> HasDriverProtocol:
    """
    Create a HasDriver, HasPlaywrightDriver, or proxied instance for testing.

    This fixture is parametrized to test all three approaches:
    - Direct Selenium (HasDriver) - skipped if Chrome not available
    - Direct Playwright (HasPlaywrightDriver) - skipped if Chromium not available
    - Proxied Selenium (HasDriverProxy wrapping HasDriver) - skipped if Chrome not available

    Args:
        request: Pytest request object
        driver: Selenium WebDriver fixture
        playwright_resources: PlaywrightResources fixture
    """
    if request.param == "selenium":
        return cast(HasDriverProtocol, TestHasDriverImpl(driver))
    elif request.param == "playwright":
        return cast(HasDriverProtocol, TestHasPlaywrightDriverImpl(playwright_resources))
    else:  # proxy-selenium
        selenium_impl = cast(HasDriverProtocol, TestHasDriverImpl(driver))
        return HasDriverProxyImpl(selenium_impl)


class TestElementFinding:
    """Tests for element finding methods."""

    def test_assert_xpath(self, has_driver_instance, base_url: str) -> None:
        """Test finding element by XPath assertion."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        has_driver_instance.assert_xpath("//h1[@id='header']")

    def test_assert_xpath_fails_when_not_found(self, has_driver_instance, base_url: str) -> None:
        """Test assert_xpath raises when element not found."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        with pytest.raises((NoSuchElementException, AssertionError)):
            has_driver_instance.assert_xpath("//div[@id='nonexistent']")

    def test_assert_selector(self, has_driver_instance, base_url: str) -> None:
        """Test finding element by CSS selector assertion."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        has_driver_instance.assert_selector("#test-div")

    def test_assert_selector_fails_when_not_found(self, has_driver_instance, base_url: str) -> None:
        """Test assert_selector raises when element not found."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        with pytest.raises((NoSuchElementException, AssertionError)):
            has_driver_instance.assert_selector("#nonexistent")

    def test_find_element_by_id(self, has_driver_instance, base_url: str) -> None:
        """Test finding element by ID."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        element = has_driver_instance.find_element_by_id("test-div")
        assert element.text == "Test Div"

    def test_find_element_by_xpath(self, has_driver_instance, base_url: str) -> None:
        """Test finding element by XPath."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        element = has_driver_instance.find_element_by_xpath("//p[@class='test-paragraph']")
        assert element.text == "Test Paragraph"

    def test_find_element_by_selector(self, has_driver_instance, base_url: str) -> None:
        """Test finding element by CSS selector."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        element = has_driver_instance.find_element_by_selector("[data-testid='test-span']")
        assert element.text == "Test Span"

    def test_find_element_by_link_text(self, has_driver_instance, base_url: str) -> None:
        """Test finding element by link text."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        element = has_driver_instance.find_element_by_link_text("Test Link")
        assert element.get_attribute("id") == "test-link"

    def test_find_elements_with_target(self, has_driver_instance, base_url: str) -> None:
        """Test finding multiple elements using Target."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.CLASS_NAME, "item"), description="list items")
        elements = has_driver_instance.find_elements(target)
        assert len(elements) == 3

    def test_find_elements_by_selector(self, has_driver_instance, base_url: str) -> None:
        """Test finding multiple elements by CSS selector."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        elements = has_driver_instance.find_elements_by_selector(".item")
        assert len(elements) == 3
        # Verify we got actual elements
        assert all(hasattr(el, "text") for el in elements)

    def test_find_elements_by_selector_no_matches(self, has_driver_instance, base_url: str) -> None:
        """Test finding elements when selector matches nothing."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        elements = has_driver_instance.find_elements_by_selector(".nonexistent-class")
        assert len(elements) == 0
        assert elements == []

    def test_find_elements_by_selector_single_match(self, has_driver_instance, base_url: str) -> None:
        """Test finding elements when selector matches single element."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        elements = has_driver_instance.find_elements_by_selector("#test-div")
        assert len(elements) == 1
        assert elements[0].text == "Test Div"

    def test_find_element_with_target(self, has_driver_instance, base_url: str) -> None:
        """Test finding single element using Target (no waiting)."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "test-div"), description="test div")
        element = has_driver_instance.find_element(target)
        assert element.text == "Test Div"

    def test_find_element_with_target_by_class(self, has_driver_instance, base_url: str) -> None:
        """Test find_element returns first element when multiple matches exist."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.CLASS_NAME, "item"), description="first item")
        element = has_driver_instance.find_element(target)
        # Should get the first item
        assert element.text in ["Item 1", "Item 2", "Item 3"]

    def test_find_element_with_target_fails_when_not_found(self, has_driver_instance, base_url: str) -> None:
        """Test find_element raises exception when element not found."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "nonexistent"), description="nonexistent element")
        with pytest.raises((NoSuchElementException, Exception)):
            has_driver_instance.find_element(target)


class TestVisibilityAndPresence:
    """Tests for visibility and presence checking methods."""

    def test_selector_is_displayed_visible_element(self, has_driver_instance, base_url):
        """Test checking if visible element is displayed."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        assert has_driver_instance.selector_is_displayed("#visible-element")

    def test_selector_is_displayed_hidden_element(self, has_driver_instance, base_url):
        """Test checking if hidden element is not displayed."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        assert not has_driver_instance.selector_is_displayed("#hidden-element")

    def test_is_displayed_with_target(self, has_driver_instance, base_url):
        """Test is_displayed with Target selector."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "visible-element"), description="visible element")
        assert has_driver_instance.is_displayed(target)

    def test_assert_selector_absent_or_hidden(self, has_driver_instance, base_url):
        """Test asserting element is absent or hidden."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        has_driver_instance.assert_selector_absent_or_hidden("#hidden-element")

    def test_assert_absent_or_hidden_with_target(self, has_driver_instance, base_url):
        """Test assert_absent_or_hidden with Target."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "hidden-element"), description="hidden element")
        has_driver_instance.assert_absent_or_hidden(target)

    def test_assert_selector_absent(self, has_driver_instance, base_url):
        """Test asserting element is completely absent from DOM."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        has_driver_instance.assert_selector_absent("#nonexistent-element")

    def test_assert_absent_with_target(self, has_driver_instance, base_url):
        """Test assert_absent with Target when element doesn't exist."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "nonexistent"), description="nonexistent element")
        has_driver_instance.assert_absent(target)

    def test_element_absent_returns_true(self, has_driver_instance, base_url):
        """Test element_absent returns True when element not in DOM."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "nonexistent"), description="nonexistent element")
        assert has_driver_instance.element_absent(target)

    def test_element_absent_returns_false(self, has_driver_instance, base_url):
        """Test element_absent returns False when element exists."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "test-div"), description="test div")
        assert not has_driver_instance.element_absent(target)

    def test_assert_disabled(self, has_driver_instance, base_url):
        """Test asserting element is disabled."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "disabled-button"), description="disabled button")
        has_driver_instance.assert_disabled(target)


class TestWaitMethods:
    """Tests for wait methods."""

    def test_wait_for_xpath(self, has_driver_instance, base_url):
        """Test waiting for element by XPath."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        element = has_driver_instance.wait_for_xpath("//h1[@id='header']")
        assert element.text == "Test Page"

    def test_wait_for_xpath_visible(self, has_driver_instance, base_url):
        """Test waiting for visible element by XPath."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        element = has_driver_instance.wait_for_xpath_visible("//div[@id='visible-element']")
        assert element.is_displayed()

    def test_wait_for_selector(self, has_driver_instance, base_url):
        """Test waiting for element by CSS selector."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        element = has_driver_instance.wait_for_selector("#test-div")
        assert element.text == "Test Div"

    def test_wait_for_present_with_target(self, has_driver_instance, base_url):
        """Test wait_for_present with Target."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "test-div"), description="test div")
        element = has_driver_instance.wait_for_present(target)
        assert element is not None

    def test_wait_for_visible_with_target(self, has_driver_instance, base_url):
        """Test wait_for_visible with Target."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "visible-element"), description="visible element")
        element = has_driver_instance.wait_for_visible(target)
        assert element.is_displayed()

    def test_wait_for_selector_visible(self, has_driver_instance, base_url):
        """Test waiting for visible element by CSS selector."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        element = has_driver_instance.wait_for_selector_visible("#visible-element")
        assert element.is_displayed()

    def test_wait_for_selector_clickable(self, has_driver_instance, base_url):
        """Test waiting for clickable element by CSS selector."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        element = has_driver_instance.wait_for_selector_clickable("#clickable-button")
        assert element.is_enabled()

    def test_wait_for_clickable_with_target(self, has_driver_instance, base_url):
        """Test wait_for_clickable with Target."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "clickable-button"), description="clickable button")
        element = has_driver_instance.wait_for_clickable(target)
        assert element.is_enabled()

    def test_wait_for_selector_absent(self, has_driver_instance, base_url):
        """Test waiting for element to be absent."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        # Element doesn't exist, so wait should succeed immediately
        has_driver_instance.wait_for_selector_absent("#nonexistent-element")

    def test_wait_for_absent_with_target(self, has_driver_instance, base_url):
        """Test wait_for_absent with Target."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "nonexistent"), description="nonexistent element")
        has_driver_instance.wait_for_absent(target)

    def test_wait_for_selector_absent_or_hidden(self, has_driver_instance, base_url):
        """Test waiting for element to be absent or hidden."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        has_driver_instance.wait_for_selector_absent_or_hidden("#hidden-element")

    def test_wait_for_absent_or_hidden_with_target(self, has_driver_instance, base_url):
        """Test wait_for_absent_or_hidden with Target."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "hidden-element"), description="hidden element")
        has_driver_instance.wait_for_absent_or_hidden(target)

    def test_wait_for_id(self, has_driver_instance, base_url):
        """Test waiting for element by ID."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        element = has_driver_instance.wait_for_id("test-div")
        assert element.get_attribute("id") == "test-div"

    def test_wait_for_element_count_of_at_least(self, has_driver_instance, base_url):
        """Test waiting for at least N elements."""
        # Skip for Playwright since _wait_on_condition_count is not implemented
        if hasattr(has_driver_instance, "page"):
            pytest.skip("wait_for_element_count_of_at_least not implemented for Playwright")
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.CLASS_NAME, "item"), description="list items")
        has_driver_instance.wait_for_element_count_of_at_least(target, 3)
        elements = has_driver_instance.find_elements(target)
        assert len(elements) >= 3

    def test_wait_timeout_with_custom_timeout(self, has_driver_instance, base_url):
        """Test that custom timeout is used."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        # Expect either SeleniumTimeoutException or PlaywrightTimeoutException
        with pytest.raises((SeleniumTimeoutException, PlaywrightTimeoutException)):
            has_driver_instance.wait_for_selector("#nonexistent", timeout=1)

    def test_wait_for_delayed_element_becomes_visible(self, has_driver_instance, base_url):
        """Test waiting for element that becomes visible after delay."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        # Element becomes visible after 1 second
        element = has_driver_instance.wait_for_selector_visible("#delayed-element", timeout=3)
        assert element.is_displayed()


class TestClickAndInteraction:
    """Tests for click and interaction methods."""

    def test_click_xpath(self, has_driver_instance, base_url):
        """Test clicking element by XPath."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        has_driver_instance.click_xpath("//button[@id='clickable-button']")
        button = has_driver_instance.find_element_by_id("clickable-button")
        assert button.text == "Clicked!"

    def test_click_selector(self, has_driver_instance, base_url):
        """Test clicking element by CSS selector."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        has_driver_instance.click_selector("#clickable-button")
        button = has_driver_instance.find_element_by_id("clickable-button")
        assert button.text == "Clicked!"

    def test_click_label(self, has_driver_instance, base_url):
        """Test clicking link by text."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        has_driver_instance.click_label("Test Link")
        # Link was clicked (href="#" so stays on same page)

    def test_click_with_target(self, has_driver_instance, base_url):
        """Test click method with Target."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        target = SimpleTarget(element_locator=(By.ID, "clickable-button"), description="clickable button")
        has_driver_instance.click(target)
        button = has_driver_instance.find_element_by_id("clickable-button")
        assert button.text == "Clicked!"


class TestFormInteraction:
    """Tests for form interaction methods."""

    def test_fill_form(self, has_driver_instance, base_url):
        """Test filling form fields."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        form = has_driver_instance.find_element_by_id("test-form")

        form_data = {"username": "testuser", "password": "testpass", "email": "test@example.com"}
        has_driver_instance.fill(form, form_data)

        # Verify fields were filled
        username = has_driver_instance.find_element_by_id("username")
        assert username.get_attribute("value") == "testuser"

        password = has_driver_instance.find_element_by_id("password")
        assert password.get_attribute("value") == "testpass"

        email = has_driver_instance.find_element_by_id("email")
        assert email.get_attribute("value") == "test@example.com"

    def test_click_submit(self, has_driver_instance, base_url):
        """Test clicking submit button on form."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        form = has_driver_instance.find_element_by_id("test-form")
        has_driver_instance.click_submit(form)

        # Verify form was submitted (result div appears)
        result = has_driver_instance.wait_for_id("form-result", timeout=2)
        assert result.text == "Form submitted!"


class TestInputValueAbstraction:
    """Tests for get_input_value abstraction."""

    def test_get_input_value_basic(self, has_driver_instance, base_url):
        """Test getting input value from a text input."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        username_input = has_driver_instance.find_element_by_id("username")

        # Set a value
        username_input.send_keys("testuser")

        # Get the value using the abstraction
        value = has_driver_instance.get_input_value(username_input)
        assert value == "testuser"

    def test_get_input_value_empty(self, has_driver_instance, base_url):
        """Test getting input value from an empty input."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        username_input = has_driver_instance.find_element_by_id("username")

        # Get value from empty input
        value = has_driver_instance.get_input_value(username_input)
        assert value == ""

    def test_get_input_value_after_js_modification(self, has_driver_instance, base_url):
        """Test getting input value after JavaScript modification."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        username_input = has_driver_instance.find_element_by_id("username")

        # Set value using JavaScript
        has_driver_instance.set_element_value(username_input, "jsvalue")

        # Get the value - this is the problematic case for Playwright
        value = has_driver_instance.get_input_value(username_input)
        assert value == "jsvalue"

    def test_get_input_value_password_field(self, has_driver_instance, base_url):
        """Test getting value from password input."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        password_input = has_driver_instance.find_element_by_id("password")

        # Set a value
        password_input.send_keys("secret123")

        # Get the value
        value = has_driver_instance.get_input_value(password_input)
        assert value == "secret123"

    def test_get_input_value_email_field(self, has_driver_instance, base_url):
        """Test getting value from email input."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        email_input = has_driver_instance.find_element_by_id("email")

        # Set a value
        email_input.send_keys("test@example.com")

        # Get the value
        value = has_driver_instance.get_input_value(email_input)
        assert value == "test@example.com"


class TestActionChainsAndKeys:
    """Tests for action chains and key sending methods."""

    def test_action_chains(self, has_driver_instance, base_url):
        """Test creating action chains."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        chains = has_driver_instance.action_chains()
        assert chains is not None

    def test_drag_and_drop(self, has_driver_instance, base_url):
        """Test drag and drop functionality."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")

        # TODO: Add actual draggable elements to basic.html for proper testing
        # For example, add:
        #   <div id="draggable" draggable="true" style="width:100px;height:100px;background:blue;">Drag me</div>
        #   <div id="droptarget" style="width:200px;height:200px;background:gray;">Drop here</div>
        # Then verify with JavaScript that droptarget contains draggable after drag_and_drop
        # e.g., assert has_driver_instance.execute_script("return document.getElementById('droptarget').contains(document.getElementById('draggable'))")

        # For now, just verify the method can be called without error
        source = has_driver_instance.find_element_by_id("test-div")
        target = has_driver_instance.find_element_by_id("visible-element")

        # Call drag_and_drop - it should not raise an exception
        # (even though these aren't actually draggable elements, the JS will execute)
        has_driver_instance.drag_and_drop(source, target)

    def test_move_to_and_click(self, has_driver_instance, base_url):
        """Test moving to element and clicking via ActionChains."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        button = has_driver_instance.find_element_by_id("clickable-button")

        # Use move_to_and_click
        has_driver_instance.move_to_and_click(button)

        # Verify button was clicked
        assert button.text == "Clicked!"

    def test_hover(self, has_driver_instance, base_url):
        """Test hovering over an element."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        hover_target = has_driver_instance.find_element_by_id("hover-target")
        hover_indicator = has_driver_instance.find_element_by_id("hover-indicator")

        # Verify indicator is initially hidden
        assert not hover_indicator.is_displayed()

        # Hover over the target element
        has_driver_instance.hover(hover_target)

        # Verify the hover made the indicator visible (using CSS :hover + sibling selector)
        assert hover_indicator.is_displayed()

    def test_send_enter(self, has_driver_instance, base_url):
        """Test sending ENTER key."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        element = has_driver_instance.find_element_by_id("enter-element")
        assert not element.is_displayed()
        element = has_driver_instance.find_element_by_id("username")
        element.click()
        has_driver_instance.send_enter(element)
        element = has_driver_instance.find_element_by_id("enter-element")
        assert element.is_displayed()

    def test_send_escape(self, has_driver_instance, base_url):
        """Test sending ESCAPE key."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        element = has_driver_instance.find_element_by_id("username")
        element.click()
        has_driver_instance.send_escape(element)
        # Key was sent (no exception)

    def test_send_backspace(self, has_driver_instance, base_url):
        """Test sending BACKSPACE key."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        element = has_driver_instance.find_element_by_id("username")
        element.send_keys("test")
        has_driver_instance.send_backspace(element)
        # Verify one character was deleted
        value = has_driver_instance.get_input_value(element)
        assert value == "tes"

    def test_aggressive_clear(self, has_driver_instance, base_url):
        """Test aggressive_clear() method for clearing input fields."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        element = has_driver_instance.find_element_by_id("username")

        # Type some text
        element.send_keys("test value that needs clearing")

        # Use aggressive_clear
        has_driver_instance.aggressive_clear(element)

        # Verify the field is cleared
        assert element.get_attribute("value") == ""


class TestFrameSwitching:
    """Tests for frame switching functionality."""

    def test_switch_to_frame_by_name(self, has_driver_instance, base_url):
        """Test switching to iframe by name."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        has_driver_instance.switch_to_frame("frame")

        # Verify we're in the frame by finding frame-specific element
        frame_header = has_driver_instance.find_element_by_id("frame-header")
        assert frame_header.text == "Inside Frame"

        # Switch back using new method
        has_driver_instance.switch_to_default_content()

    def test_switch_to_frame_by_id(self, has_driver_instance, base_url):
        """Test switching to iframe by id (frame has name='frame' and id could be different)."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        # The frame has name="frame" - the method should work for both name and id
        has_driver_instance.switch_to_frame("frame")

        # Verify we're in the frame
        frame_header = has_driver_instance.find_element_by_id("frame-header")
        assert frame_header.text == "Inside Frame"

        # Switch back
        has_driver_instance.switch_to_default_content()

    def test_switch_to_frame_by_element(self, has_driver_instance, base_url):
        """Test switching to iframe by element reference."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")

        # Find the frame element first
        frame_element = has_driver_instance.find_element_by_selector("[name='frame']")

        # Switch to it by element
        has_driver_instance.switch_to_frame(frame_element)

        # Verify we're in the frame
        frame_header = has_driver_instance.find_element_by_id("frame-header")
        assert frame_header.text == "Inside Frame"

        # Switch back
        has_driver_instance.switch_to_default_content()

    def test_switch_to_default_content(self, has_driver_instance, base_url):
        """Test switching back to default content."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")

        # Switch to frame
        has_driver_instance.switch_to_frame("frame")

        # Verify we're in the frame
        frame_header = has_driver_instance.find_element_by_id("frame-header")
        assert frame_header.text == "Inside Frame"

        # Switch back to default content
        has_driver_instance.switch_to_default_content()

        # Verify we're back in main content (frame-header shouldn't be accessible now)
        header = has_driver_instance.find_element_by_id("header")
        assert header.text == "Test Page"


class TestAlertHandling:
    """Tests for alert handling."""

    def test_accept_alert(self, has_driver_instance, base_url):
        """Test accepting browser alert."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        has_driver_instance.click_selector("#alert-button")

        # Accept the alert
        has_driver_instance.accept_alert()

        # Verify we're back on the main page
        header = has_driver_instance.find_element_by_id("header")
        assert header.text == "Test Page"


class TestCookieManagement:
    """Tests for cookie management."""

    def test_get_cookies(self, has_driver_instance, base_url):
        """Test getting all cookies."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")

        # Get all cookies (test server sets test_cookie automatically)
        cookies = has_driver_instance.get_cookies()

        # Verify cookies is a list
        assert isinstance(cookies, list)
        assert len(cookies) > 0

        # Verify our test cookie is in the list
        cookie_names = [cookie["name"] for cookie in cookies]
        assert "test_cookie" in cookie_names

        # Find and verify the test cookie value
        test_cookie = next(cookie for cookie in cookies if cookie["name"] == "test_cookie")
        assert test_cookie["value"] == "test_value"


class TestUtilityMethods:
    """Tests for utility methods."""

    def test_navigate_to(self, has_driver_instance: HasDriverProtocol, base_url: str, request) -> None:
        """Test navigating to a URL and changing pages."""
        # Navigate to first page
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        assert "basic.html" in has_driver_instance.current_url
        # Verify first page loaded by checking for expected element
        header = has_driver_instance.find_element_by_id("header")
        assert header.text == "Test Page"

        # Navigate to second page
        has_driver_instance.navigate_to(f"{base_url}/frame.html")
        assert "frame.html" in has_driver_instance.current_url
        # Verify we actually navigated to a different page
        frame_header = has_driver_instance.find_element_by_id("frame-header")
        assert frame_header.text == "Inside Frame"

        # Verify the original element is no longer present
        target = SimpleTarget((By.ID, "header"), "header element")
        elements = has_driver_instance.find_elements(target)
        assert len(elements) == 0

    def test_re_get_with_query_params_adds_question_mark(self, has_driver_instance, base_url):
        """Test adding query params to URL without existing params."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        has_driver_instance.re_get_with_query_params("foo=bar")
        assert "?foo=bar" in has_driver_instance.current_url

    def test_re_get_with_query_params_appends_to_existing(self, has_driver_instance, base_url):
        """Test adding query params to URL with existing params."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html?existing=param")
        has_driver_instance.re_get_with_query_params("foo=bar")
        current_url = has_driver_instance.current_url
        assert "existing=param" in current_url
        assert "foo=bar" in current_url

    def test_prepend_timeout_message(self, has_driver_instance, request):
        """Test prepending message to timeout exception."""
        backend = request.node.callspec.params.get("has_driver_instance")
        if backend == "selenium":
            original_selenium_exc = SeleniumTimeoutException(msg="original message")
            new_selenium_exception = has_driver_instance.prepend_timeout_message(original_selenium_exc, "New prefix:")
            assert "New prefix:" in new_selenium_exception.msg
            assert "original message" in new_selenium_exception.msg
        else:  # playwright
            original_playwright_exc = PlaywrightTimeoutException("original message")
            new_playwright_exception = has_driver_instance.prepend_timeout_message(
                original_playwright_exc, "New prefix:"
            )
            assert "New prefix:" in str(new_playwright_exception)
            assert "original message" in str(new_playwright_exception)


class TestJavaScriptExecution:
    """Tests for JavaScript execution methods."""

    def test_execute_script_returns_value(self, has_driver_instance, base_url):
        """Test executing JavaScript and returning value."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        result = has_driver_instance.execute_script("return 42;")
        assert result == 42

    def test_execute_script_with_arguments(self, has_driver_instance, base_url):
        """Test executing JavaScript with arguments."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        result = has_driver_instance.execute_script("return arguments[0] + arguments[1];", 10, 20)
        assert result == 30

    def test_execute_script_with_element(self, has_driver_instance, base_url):
        """Test executing JavaScript with element argument."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        element = has_driver_instance.find_element_by_id("test-div")
        result = has_driver_instance.execute_script("return arguments[0].textContent;", element)
        assert result == "Test Div"

    def test_set_local_storage(self, has_driver_instance, base_url):
        """Test setting localStorage value."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        has_driver_instance.set_local_storage("testKey", '"testValue"')

        # Verify localStorage was set
        result = has_driver_instance.execute_script('return window.localStorage.getItem("testKey");')
        assert result == "testValue"

    def test_remove_local_storage(self, has_driver_instance, base_url):
        """Test removing localStorage value."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        # First set a value
        has_driver_instance.execute_script('window.localStorage.setItem("testKey", "testValue");')

        # Now remove it
        has_driver_instance.remove_local_storage("testKey")

        # Verify it was removed
        result = has_driver_instance.execute_script('return window.localStorage.getItem("testKey");')
        assert result is None

    def test_scroll_into_view(self, has_driver_instance, base_url):
        """Test scrolling element into view."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        element = has_driver_instance.find_element_by_id("test-div")

        # Scroll into view (should not raise exception)
        has_driver_instance.scroll_into_view(element)

        # Verify element is visible
        assert element.is_displayed()

    def test_set_element_value(self, has_driver_instance, base_url):
        """Test setting element value directly."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        input_element = has_driver_instance.find_element_by_id("username")

        # Set value using JavaScript
        has_driver_instance.set_element_value(input_element, "newvalue")

        # Verify value was set using the abstraction
        value = has_driver_instance.get_input_value(input_element)
        assert value == "newvalue"

    def test_execute_script_click(self, has_driver_instance, base_url):
        """Test clicking element via JavaScript."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        button = has_driver_instance.find_element_by_id("clickable-button")

        # Click using JavaScript
        has_driver_instance.execute_script_click(button)

        # Verify button was clicked
        assert button.text == "Clicked!"


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


class TestScreenshots:
    """Tests for screenshot functionality."""

    def test_save_screenshot(self, has_driver_instance, base_url, tmp_path):
        """Test saving a screenshot to a file."""
        import os

        has_driver_instance.navigate_to(f"{base_url}/basic.html")

        # Save screenshot to temp file
        screenshot_path = str(tmp_path / "test_screenshot.png")
        has_driver_instance.save_screenshot(screenshot_path)

        # Verify file was created
        assert os.path.exists(screenshot_path)

        # Verify it's a PNG file (check magic bytes)
        with open(screenshot_path, "rb") as f:
            header = f.read(8)
            # PNG magic bytes: 89 50 4E 47 0D 0A 1A 0A
            assert header == b"\x89PNG\r\n\x1a\n"

        # Verify file has content
        assert os.path.getsize(screenshot_path) > 0

    def test_get_screenshot_as_png(self, has_driver_instance, base_url):
        """Test getting a screenshot as PNG bytes."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")

        # Get screenshot as bytes
        screenshot_bytes = has_driver_instance.get_screenshot_as_png()

        # Verify it's bytes
        assert isinstance(screenshot_bytes, bytes)

        # Verify it's non-empty
        assert len(screenshot_bytes) > 0

        # Verify it's a PNG file (check magic bytes)
        # PNG magic bytes: 89 50 4E 47 0D 0A 1A 0A
        assert screenshot_bytes[:8] == b"\x89PNG\r\n\x1a\n"


class TestAccessibility:
    """Tests for axe_eval accessibility testing."""

    def test_axe_eval_basic(self, has_driver_instance, base_url):
        """Test basic axe_eval functionality returns results."""
        has_driver_instance.navigate_to(f"{base_url}/accessibility.html")
        results = has_driver_instance.axe_eval()

        # Should have some violations in our test page
        violations = results.violations()
        assert len(violations) > 0

    def test_axe_eval_with_context(self, has_driver_instance, base_url):
        """Test axe_eval with context parameter to limit scope."""
        has_driver_instance.navigate_to(f"{base_url}/accessibility.html")

        # Run axe on just the good section
        results = has_driver_instance.axe_eval(context="#good-section")

        # Good section should have fewer/no violations
        violations = results.violations()
        # We expect fewer violations when scoped to good section
        assert isinstance(violations, list)

    def test_axe_eval_assert_passes(self, has_driver_instance, base_url):
        """Test axe_eval assert_passes for specific rules."""
        has_driver_instance.navigate_to(f"{base_url}/accessibility.html")
        results = has_driver_instance.axe_eval()

        # Test that we can check if a specific rule passed
        # document-title should pass on our test page (we have a <title> element)
        results.assert_passes("document-title")

    def test_axe_eval_assert_does_not_violate(self, has_driver_instance, base_url):
        """Test axe_eval assert_does_not_violate for specific rules."""
        has_driver_instance.navigate_to(f"{base_url}/accessibility.html")
        results = has_driver_instance.axe_eval(context="#good-section")

        # Good section should not violate certain rules
        # This is a sanity check - if this fails, our test fixture needs adjustment
        try:
            results.assert_does_not_violate("aria-roles")
        except AssertionError:
            pytest.fail("Good section should not have aria-roles violations")

    def test_axe_eval_violations_with_impact(self, has_driver_instance, base_url):
        """Test filtering violations by impact level."""
        has_driver_instance.navigate_to(f"{base_url}/accessibility.html")
        results = has_driver_instance.axe_eval()

        # Get violations with at least moderate impact
        moderate_violations = results.violations_with_impact_of_at_least("moderate")
        all_violations = results.violations()

        # moderate+ violations should be subset of all violations
        assert len(moderate_violations) <= len(all_violations)
        assert isinstance(moderate_violations, list)

    def test_axe_eval_with_axe_skip(self, driver, base_url):
        """Test that axe_eval returns NullAxeResults when axe_skip is True."""

        # Create a test instance with axe_skip=True
        class TestHasDriverSkipAxe(TestHasDriverImpl):
            axe_skip = True

        instance = TestHasDriverSkipAxe(driver)
        instance.navigate_to(f"{base_url}/accessibility.html")
        results = instance.axe_eval()

        # Should return NullAxeResults which has no violations
        violations = results.violations()
        assert len(violations) == 0

        # All assertions should pass silently with NullAxeResults
        results.assert_passes("any-rule")
        results.assert_does_not_violate("any-rule")
        results.assert_no_violations_with_impact_of_at_least("critical")


class TestPageSource:
    """Test page_source property."""

    def test_page_source_contains_content(self, has_driver_instance, base_url):
        """Test that page_source contains actual page content."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")

        source = has_driver_instance.page_source

        # Should contain the test div with known ID
        assert 'id="test-div"' in source

        # Should contain some visible text content
        assert "Test Div" in source

    def test_page_source_updates_after_navigation(self, has_driver_instance, base_url):
        """Test that page_source updates when navigating to different pages."""
        # Navigate to first page
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        source1 = has_driver_instance.page_source

        # Navigate to different page
        has_driver_instance.navigate_to(f"{base_url}/accessibility.html")
        source2 = has_driver_instance.page_source

        # Sources should be different
        assert source1 != source2

        # Second source should contain content from accessibility page
        assert "good-section" in source2 or "bad-section" in source2


class TestPageTitle:
    """Test page_title property."""

    def test_page_title_basic(self, has_driver_instance, base_url):
        """Test that page_title returns the page title."""
        has_driver_instance.navigate_to(f"{base_url}/basic.html")

        title = has_driver_instance.page_title

        # Should match the title from basic.html
        assert title == "Basic Test Page"

    def test_page_title_updates_after_navigation(self, has_driver_instance, base_url):
        """Test that page_title updates when navigating to different pages."""
        # Navigate to first page
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        title1 = has_driver_instance.page_title

        # Navigate to different page
        has_driver_instance.navigate_to(f"{base_url}/accessibility.html")
        title2 = has_driver_instance.page_title

        # Titles should be different
        assert title1 != title2

        # Verify titles match expected values
        assert title1 == "Basic Test Page"
        assert title2 == "Accessibility Test Page"
