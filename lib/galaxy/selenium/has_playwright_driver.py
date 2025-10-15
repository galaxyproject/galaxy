"""Playwright-backed implementation of the HasDriver abstraction layer.

This module provides a Playwright-based implementation that mirrors the API of
has_driver.py, allowing Galaxy tests to run with either Selenium or Playwright
backends with minimal code changes.

Overview
--------
HasPlaywrightDriver provides a high-level interface for browser automation using
Playwright, with the same API surface as HasDriver (Selenium-based). This allows
test code to be backend-agnostic - the same test can run against both Selenium
and Playwright implementations.

Key Features
------------
- Element finding and interaction (click, hover, drag-and-drop, etc.)
- Explicit wait methods for various element states (visible, clickable, absent, etc.)
- Frame/iframe switching and navigation
- JavaScript execution and page manipulation
- Form filling and submission
- Cookie management and local storage
- Accessibility testing with axe-core
- Exception handling and timeout management

Usage Example
-------------
To use this mixin, create a class that provides the required attributes:

    from playwright.sync_api import sync_playwright
    from galaxy.selenium.has_playwright_driver import HasPlaywrightDriver

    class MyTestClass(HasPlaywrightDriver):
        def __init__(self, page):
            self.page = page
            self.default_timeout = 10.0

        def timeout_for(self, **kwds):
            return kwds.get("timeout", self.default_timeout)

    # In your test
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        test = MyTestClass(page)

        # Use the high-level API
        test.navigate_to("https://example.com")
        test.click_selector("#my-button")
        test.wait_for_selector_visible(".result")
        element = test.find_element_by_id("content")

API Compatibility with HasDriver
---------------------------------
This implementation maintains API compatibility with HasDriver (Selenium), with
the following considerations:

**Fully Compatible Methods:**
- Element finding: find_element_by_id, find_element_by_selector, find_elements, etc.
- Waiting: wait_for_selector, wait_for_visible, wait_for_clickable, etc.
- Clicking: click_selector, click_xpath, click_label, etc.
- Navigation: navigate_to, re_get_with_query_params
- Assertions: assert_selector_absent_or_hidden, assert_disabled, etc.
- JavaScript: execute_script, execute_script_click, set_element_value
- Forms: fill, click_submit
- Frames: switch_to_frame, switch_to_default_content
- Accessibility: axe_eval (with context and write_to parameters)
- Cookies: get_cookies
- Storage: set_local_storage, remove_local_storage

**Known Limitations:**
1. wait_for_element_count_of_at_least() - Not implemented (raises NotImplementedError)
   - Playwright doesn't have an equivalent to Selenium's element count waiting
   - Use wait_for_present() and then check length of find_elements() instead

2. Custom wait conditions - Not implemented (raises NotImplementedError)
   - Selenium's WebDriverWait.until() with custom conditions has no direct equivalent
   - Use Playwright's built-in wait methods or page.wait_for_function() instead

3. Alert handling - Different approach required
   - Playwright requires setting up event handlers before triggering dialogs
   - accept_alert() sets up a one-time handler, but may need adjustment for your use case

Implementation Details
----------------------
**Locator Strategy:**
Playwright uses CSS selectors and XPath natively. This implementation automatically
converts Selenium locator strategies to Playwright selectors:
- By.ID → #id
- By.CLASS_NAME → .classname
- By.CSS_SELECTOR → direct use
- By.XPATH → direct use (Playwright supports XPath)
- By.LINK_TEXT → text=...
- By.NAME → [name="..."]

**Wait Strategy:**
Unlike Selenium's explicit WebDriverWait, Playwright has built-in auto-waiting for
most actions. This implementation uses page.wait_for_selector() with different
states: 'attached', 'detached', 'visible', 'hidden'.

**Element References:**
Returns WebElementProtocol-compatible PlaywrightElement wrappers around Playwright's
ElementHandle objects. This provides a consistent interface across both backends.

**Frame Handling:**
Playwright doesn't have Selenium's "switch to" concept. This implementation tracks
the current frame in _current_frame and uses _frame_or_page property to provide
transparent access to the correct context.

Thread Safety
-------------
This class is not thread-safe. Each Playwright Page should have its own
HasPlaywrightDriver instance, and should only be accessed from a single thread.

See Also
--------
- has_driver.py: The Selenium-based implementation with identical API
- web_element_protocol.py: The WebElementProtocol interface for element compatibility
- playwright_element.py: The PlaywrightElement wrapper implementation
- wait_methods_mixin.py: Shared wait method implementations
"""

import abc
from typing import (
    Generic,
    NamedTuple,
    Optional,
    Union,
)

from playwright.sync_api import (
    Browser,
    ElementHandle,
    Frame,
    FrameLocator,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutException,
)

from galaxy.navigation.components import Target
from ._wait import (
    TimeoutAssertionError,
    wait_on,
)
from .axe_results import (
    AxeResults,
    NullAxeResults,
    RealAxeResults,
)
from .has_driver import (
    DEFAULT_AXE_SCRIPT_URL,
    get_axe_script,
    TimeoutMessageMixin,
)
from .has_driver_protocol import (
    BackendType,
    Cookie,
    TimeoutCallback,
    WaitTypeT,
)
from .playwright_element import PlaywrightElement
from .wait_methods_mixin import WaitMethodsMixin
from .web_element_protocol import WebElementProtocol

UNSPECIFIED_TIMEOUT = object()


class PlaywrightResources(NamedTuple):
    """
    Resources needed for Playwright driver lifecycle management.

    This bundles together all the Playwright objects needed to properly
    clean up a browser session.

    Attributes:
        playwright: Main Playwright instance (needs .stop() on cleanup)
        browser: Browser instance (needs .close() on cleanup)
        page: Page instance for browser automation
    """

    playwright: Playwright
    browser: Browser
    page: Page


class PlaywrightKeys:
    """Mapping of Selenium Keys to Playwright key names."""

    ENTER = "Enter"
    ESCAPE = "Escape"
    BACKSPACE = "Backspace"
    TAB = "Tab"
    SPACE = " "
    ARROW_DOWN = "ArrowDown"
    ARROW_UP = "ArrowUp"
    ARROW_LEFT = "ArrowLeft"
    ARROW_RIGHT = "ArrowRight"


class PlaywrightBy:
    """Locator strategy constants matching Selenium's By class."""

    ID = "id"
    XPATH = "xpath"
    LINK_TEXT = "link_text"
    PARTIAL_LINK_TEXT = "partial_link_text"
    NAME = "name"
    TAG_NAME = "tag_name"
    CLASS_NAME = "class_name"
    CSS_SELECTOR = "css_selector"


class HasPlaywrightDriver(TimeoutMessageMixin, WaitMethodsMixin, Generic[WaitTypeT]):
    """Playwright-backed implementation of HasDriver interface."""

    by: type[PlaywrightBy] = PlaywrightBy
    keys: type[PlaywrightKeys] = PlaywrightKeys
    axe_script_url: str = DEFAULT_AXE_SCRIPT_URL
    axe_skip: bool = False
    _current_frame: Optional[Union[Frame, FrameLocator]] = None
    _playwright_resources: PlaywrightResources

    @property
    def page(self) -> Page:
        """Access the Playwright Page from resources."""
        return self._playwright_resources.page

    @property
    def backend_type(self) -> BackendType:
        """Identify this as the Playwright backend implementation."""
        return "playwright"

    @property
    @abc.abstractmethod
    def timeout_handler(self) -> TimeoutCallback:
        """Get timeout handler for application specific wait types."""
        ...

    def _selenium_locator_to_playwright_selector(self, by: str, value: str) -> str:
        """
        Convert Selenium By locator (with spaces) to Playwright selector.

        Args:
            by: Selenium locator strategy (e.g., 'class name', 'css selector')
            value: Locator value

        Returns:
            Playwright-compatible selector string
        """
        if by == "id":
            return f"#{value}"
        elif by == "css selector":
            return value
        elif by == "xpath":
            return f"xpath={value}"
        elif by == "class name":
            return f".{value}"
        elif by == "name":
            return f"[name='{value}']"
        elif by == "tag name":
            return value
        elif by == "link text":
            return f"text={value}"
        elif by == "partial link text":
            return f"text=/{value}/"
        else:
            raise ValueError(f"Unsupported Selenium locator strategy: {by}")

    def _target_to_playwright_selector(self, target: Target) -> str:
        """
        Convert a Target object to Playwright selector.

        Target objects use Selenium By constants, so we use the Selenium converter.

        Args:
            target: Target object with element_locator

        Returns:
            Playwright-compatible selector string
        """
        by, value = target.element_locator
        return self._selenium_locator_to_playwright_selector(by, value)

    @property
    def current_url(self) -> str:
        """
        Get the current page URL.

        Returns:
            The current URL
        """
        return self.page.url

    @property
    def page_source(self) -> str:
        """
        Get the HTML source of the current page.

        Returns:
            The page HTML as a string
        """
        return self.page.content()

    @property
    def page_title(self) -> str:
        """
        Get the title of the current page.

        Returns:
            The page title as a string
        """
        return self.page.title()

    def navigate_to(self, url: str) -> None:
        """
        Navigate to a URL.

        Args:
            url: The URL to navigate to
        """
        self.page.goto(url)

    def re_get_with_query_params(self, params_str: str):
        """Add query parameters to current URL and reload."""
        current_url = self.page.url
        if "?" not in current_url:
            current_url += "?"
        new_url = current_url + params_str
        self.page.goto(new_url)

    def assert_xpath(self, xpath: str):
        """Assert element exists by XPath."""
        selector = f"xpath={xpath}"
        element = self._frame_or_page.locator(selector).first
        assert element.count() > 0, f"Element not found with xpath: {xpath}"

    def assert_selector(self, selector: str):
        """Assert element exists by CSS selector."""
        element = self._frame_or_page.locator(selector).first
        assert element.count() > 0, f"Element not found with selector: {selector}"

    def assert_selector_absent_or_hidden(self, selector: str):
        """Assert element is absent or hidden."""
        elements = self._frame_or_page.locator(selector).all()
        for element in elements:
            assert not element.is_visible()

    def assert_absent_or_hidden(self, selector_template: Target):
        """Assert element is absent or hidden using Target."""
        selector = self._target_to_playwright_selector(selector_template)
        elements = self._frame_or_page.locator(selector).all()
        for element in elements:
            assert not element.is_visible()

    def assert_absent_or_hidden_after_transitions(self, selector_template: Target, **kwds) -> None:
        """
        Assert element is absent or hidden (convenience method for subclasses to override with retry logic).

        This is a basic implementation that calls assert_absent_or_hidden.
        Subclasses may decorate or override this method with retry logic for handling
        transitions where elements may become stale.

        Args:
            selector_template: Target selector for the element
            **kwds: Additional keyword arguments
        """
        return self.assert_absent_or_hidden(selector_template, **kwds)

    def assert_disabled(self, selector_template: Target):
        """Assert element is disabled."""
        selector = self._target_to_playwright_selector(selector_template)
        elements = self._frame_or_page.locator(selector).all()
        assert len(elements) > 0, f"No elements found for {selector_template.description}"
        for element in elements:
            assert not element.is_enabled()

    def selector_is_displayed(self, selector: str) -> bool:
        """Check if element is displayed."""
        element = self._frame_or_page.locator(selector).first
        return element.is_visible()

    def is_displayed(self, selector_template: Target) -> bool:
        """Check if element is displayed using Target."""
        selector = self._target_to_playwright_selector(selector_template)
        element = self._frame_or_page.locator(selector).first
        return element.is_visible()

    def assert_selector_absent(self, selector: str):
        """Assert element is completely absent from DOM."""
        count = self._frame_or_page.locator(selector).count()
        assert count == 0, f"Expected 0 elements but found {count} for selector: {selector}"

    def find_elements(self, selector_template: Target) -> list[WebElementProtocol]:
        """
        Find all elements matching the Target selector.

        Args:
            selector_template: Target selector

        Returns:
            List of PlaywrightElement objects
        """
        selector = self._target_to_playwright_selector(selector_template)
        locator = self._frame_or_page.locator(selector)
        # Get all element handles and wrap them
        count = locator.count()
        return [PlaywrightElement(locator.nth(i).element_handle(), self) for i in range(count)]

    def find_element(self, selector_template: Target) -> WebElementProtocol:
        """Find first element matching Target (no waiting)."""
        selector = self._target_to_playwright_selector(selector_template)
        element_handle = self._frame_or_page.locator(selector).first.element_handle()
        return PlaywrightElement(element_handle, self)

    def assert_absent(self, selector_template: Target) -> None:
        """Assert element is absent using Target."""
        elements = self.find_elements(selector_template)
        if len(elements) != 0:
            description = selector_template.description
            any_displayed = False
            for element in elements:
                # Check if visible
                any_displayed = any_displayed or element.is_displayed()
            msg = f"Expected DOM elements [{elements}] to be empty for selector target {description} - any actually displayed? [{any_displayed}]"
            raise AssertionError(msg)

    def element_absent(self, selector_template: Target) -> bool:
        """Check if element is absent."""
        return len(self.find_elements(selector_template)) == 0

    def find_element_by_link_text(self, text: str, element: Optional[ElementHandle] = None) -> WebElementProtocol:
        """Find element by link text."""
        if element is not None:
            # Find within element context - need to use element as locator root
            raise NotImplementedError("Finding within element context not yet implemented")
        selector = f"text={text}"
        element_handle = self._frame_or_page.locator(selector).first.element_handle()
        return PlaywrightElement(element_handle, self)

    def find_element_by_xpath(self, xpath: str, element: Optional[ElementHandle] = None) -> WebElementProtocol:
        """Find element by XPath."""
        if element is not None:
            raise NotImplementedError("Finding within element context not yet implemented")
        selector = f"xpath={xpath}"
        element_handle = self._frame_or_page.locator(selector).first.element_handle()
        return PlaywrightElement(element_handle, self)

    def find_element_by_id(self, id: str, element: Optional[ElementHandle] = None) -> WebElementProtocol:
        """Find element by ID."""
        if element is not None:
            raise NotImplementedError("Finding within element context not yet implemented")
        selector = f"#{id}"
        element_handle = self._frame_or_page.locator(selector).first.element_handle()
        return PlaywrightElement(element_handle, self)

    def find_element_by_selector(self, selector: str, element: Optional[ElementHandle] = None) -> WebElementProtocol:
        """Find element by CSS selector."""
        if element is not None:
            raise NotImplementedError("Finding within element context not yet implemented")
        element_handle = self._frame_or_page.locator(selector).first.element_handle()
        return PlaywrightElement(element_handle, self)

    def find_elements_by_selector(
        self, selector: str, element: Optional[ElementHandle] = None
    ) -> list[WebElementProtocol]:
        """
        Find multiple elements by CSS selector.

        Args:
            selector: CSS selector string
            element: Optional parent element to search within (not yet implemented)

        Returns:
            List of WebElementProtocol elements
        """
        if element is not None:
            raise NotImplementedError("Finding within element context not yet implemented")
        element_handles = self._frame_or_page.locator(selector).all()
        return [PlaywrightElement(handle.element_handle(), self) for handle in element_handles]

    def get_input_value(self, element: WebElementProtocol) -> str:
        """
        Get the value of an input element.

        This provides a unified interface for getting input values across both
        Selenium and Playwright backends. For Playwright, this uses the
        PlaywrightElement's get_attribute("value") which internally uses
        input_value() for proper value retrieval.

        Args:
            element: The input element to get the value from

        Returns:
            The current value of the input element, or empty string if no value
        """
        # The PlaywrightElement.get_attribute("value") already handles the
        # special case of using input_value() for input elements
        value = element.get_attribute("value")
        return value if value is not None else ""

    def _timeout_in_ms(self, timeout=UNSPECIFIED_TIMEOUT, wait_type: Optional[WaitTypeT] = None, **kwds) -> float:
        """
        Convert timeout from seconds to milliseconds.

        Returns:
            Timeout in milliseconds for Playwright
        """

        if timeout is UNSPECIFIED_TIMEOUT:
            timeout = self.timeout_handler(wait_type)

        return timeout * 1000

    # Implementation of WaitMethodsMixin abstract methods for Playwright
    def _wait_on_condition_present(self, locator_tuple: tuple, message: str, **kwds) -> WebElementProtocol:
        """Wait for element to be present in DOM."""
        timeout_ms = self._timeout_in_ms(**kwds)
        selector = self._selenium_locator_to_playwright_selector(*locator_tuple)
        try:
            if self._current_frame is not None:
                frame_locator = self._frame_or_page
                frame_locator.locator(selector).wait_for(state="attached", timeout=timeout_ms)
                element_handle = frame_locator.locator(selector).first.element_handle()
            else:
                self._frame_or_page.wait_for_selector(selector, state="attached", timeout=timeout_ms)
                element_handle = self._frame_or_page.locator(selector).first.element_handle()
            return PlaywrightElement(element_handle, self)
        except PlaywrightTimeoutException as e:
            raise PlaywrightTimeoutException(self._timeout_message(message)) from e

    def _wait_on_condition_visible(self, locator_tuple: tuple, message: str, **kwds) -> WebElementProtocol:
        """Wait for element to be visible."""
        timeout_ms = self._timeout_in_ms(**kwds)
        selector = self._selenium_locator_to_playwright_selector(*locator_tuple)
        try:
            if self._current_frame is not None:
                frame_locator = self._frame_or_page
                frame_locator.locator(selector).wait_for(state="visible", timeout=timeout_ms)
                element_handle = frame_locator.locator(selector).first.element_handle()
            else:
                self._frame_or_page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
                element_handle = self._frame_or_page.locator(selector).first.element_handle()
            return PlaywrightElement(element_handle, self)
        except PlaywrightTimeoutException as e:
            raise PlaywrightTimeoutException(self._timeout_message(message)) from e

    def _wait_on_condition_clickable(self, locator_tuple: tuple, message: str, **kwds) -> WebElementProtocol:
        """Wait for element to be clickable."""
        timeout_ms = self._timeout_in_ms(**kwds)
        selector = self._selenium_locator_to_playwright_selector(*locator_tuple)
        try:
            # Playwright doesn't have explicit "clickable" state, use visible + enabled
            all_locator = self._frame_or_page.locator(selector)
            locator = all_locator.first
            self._frame_or_page.wait_for_selector(selector, state="visible", timeout=timeout_ms)

            # Wait for element to be enabled
            def is_enabled() -> bool:
                return locator.is_enabled()

            wait_on(is_enabled, "locator to be enabled", timeout=timeout_ms / 1000)

            element_handle = locator.element_handle()
            return PlaywrightElement(element_handle, self)
        except TimeoutAssertionError as e:
            # found the element but it never became enabled, TODO: richer error message
            raise PlaywrightTimeoutException(self._timeout_message(message)) from e
        except PlaywrightTimeoutException as e:
            raise PlaywrightTimeoutException(self._timeout_message(message)) from e

    def _wait_on_condition_invisible(self, locator_tuple: tuple, message: str, **kwds) -> None:
        """Wait for element to be invisible or absent."""
        timeout_ms = self._timeout_in_ms(**kwds)
        selector = self._selenium_locator_to_playwright_selector(*locator_tuple)
        try:
            self._frame_or_page.wait_for_selector(selector, state="hidden", timeout=timeout_ms)
            return None
        except PlaywrightTimeoutException as e:
            raise PlaywrightTimeoutException(self._timeout_message(message)) from e

    def _wait_on_condition_absent(self, locator_tuple: tuple, message: str, **kwds) -> None:
        """Wait for element to be completely absent from DOM."""
        timeout_ms = self._timeout_in_ms(**kwds)
        selector = self._selenium_locator_to_playwright_selector(*locator_tuple)
        try:
            self._frame_or_page.wait_for_selector(selector, state="detached", timeout=timeout_ms)
            return None
        except PlaywrightTimeoutException as e:
            raise PlaywrightTimeoutException(self._timeout_message(message)) from e

    def _wait_on_condition_count(self, locator_tuple: tuple, n: int, message: str, **kwds) -> None:
        """Wait for at least N elements."""
        raise NotImplementedError("wait_for_element_count_of_at_least not yet implemented for Playwright")

    def _wait_on_custom(self, condition_func, message: str, **kwds) -> None:
        """Wait on custom condition function."""
        raise NotImplementedError("Custom wait conditions not yet implemented for Playwright")

    def _unwrap_element(self, element: WebElementProtocol) -> ElementHandle:
        """
        Unwrap a PlaywrightElement to get the underlying ElementHandle.

        Args:
            element: WebElementProtocol (PlaywrightElement wrapper)

        Returns:
            The underlying ElementHandle
        """
        if isinstance(element, PlaywrightElement):
            return element.element_handle
        # For type safety, this should always be a PlaywrightElement in this driver
        raise TypeError(f"Expected PlaywrightElement, got {type(element)}")

    def double_click(self, element: WebElementProtocol) -> None:
        """
        Double-click an element.

        Args:
            element: The element to double-click
        """
        self._double_click(self._unwrap_element(element))

    def _double_click(self, element: ElementHandle) -> None:
        """Internal implementation of double-click."""
        element.dblclick()

    def click(self, selector_template: Target) -> None:
        """
        Click an element using Target selector.

        Args:
            selector_template: Target selector for the element
        """
        selector = self._target_to_playwright_selector(selector_template)
        self._frame_or_page.locator(selector).first.click()

    def click_xpath(self, xpath: str) -> None:
        """
        Click element by XPath.

        Args:
            xpath: XPath selector
        """
        selector = f"xpath={xpath}"
        self._frame_or_page.locator(selector).first.click()

    def click_label(self, text: str) -> None:
        """
        Click link by text.

        Args:
            text: Link text to click
        """
        selector = f"text={text}"
        self._frame_or_page.locator(selector).first.click()

    def click_selector(self, selector: str) -> None:
        """
        Click element by CSS selector.

        Args:
            selector: CSS selector
        """
        self._frame_or_page.locator(selector).first.click()

    def send_enter(self, element: Optional[WebElementProtocol] = None) -> None:
        """
        Send ENTER key.

        Args:
            element: Optional element to send key to. If None, sends to page.
        """
        if element is None:
            self.page.keyboard.press(self.keys.ENTER)
        else:
            self._send_key_to_element(self.keys.ENTER, self._unwrap_element(element))

    def send_escape(self, element: Optional[WebElementProtocol] = None) -> None:
        """
        Send ESCAPE key.

        Args:
            element: Optional element to send key to. If None, sends to page.
        """
        if element is None:
            self.page.keyboard.press(self.keys.ESCAPE)
        else:
            self._send_key_to_element(self.keys.ESCAPE, self._unwrap_element(element))

    def send_backspace(self, element: Optional[WebElementProtocol] = None) -> None:
        """
        Send BACKSPACE key.

        Args:
            element: Optional element to send key to. If None, sends to page.
        """
        if element is None:
            self.page.keyboard.press(self.keys.BACKSPACE)
        else:
            self._send_key_to_element(self.keys.BACKSPACE, self._unwrap_element(element))

    def aggressive_clear(self, element: WebElementProtocol) -> None:
        """
        Clear input element value using JavaScript and backspaces.

        This is useful when a simple .clear() doesn't work due to event handlers
        or framework-specific behavior.

        Args:
            element: The input element to clear
        """
        unwrapped = self._unwrap_element(element)
        # First clear via JavaScript
        self.page.evaluate("element => element.value = ''", unwrapped)
        # Then send backspaces to trigger any input events
        for _ in range(25):
            unwrapped.press(self.keys.BACKSPACE)

    def _send_key_to_element(self, key: str, element: ElementHandle) -> None:
        """
        Internal: Send a key press to a specific element.

        Args:
            key: The key to send
            element: ElementHandle to send key to
        """
        element.press(key)

    def hover(self, element: WebElementProtocol) -> None:
        """
        Hover over an element (move mouse to element without clicking).

        Args:
            element: The element to hover over
        """
        self._hover(self._unwrap_element(element))

    def _hover(self, element: ElementHandle) -> None:
        """Internal implementation of hover."""
        element.hover()

    def move_to_and_click(self, element: WebElementProtocol) -> None:
        """
        Move to an element and click it.

        This is useful when a simple click doesn't work due to element positioning.

        Args:
            element: The element to move to and click
        """
        self._move_to_and_click(self._unwrap_element(element))

    def _move_to_and_click(self, element: ElementHandle) -> None:
        """Internal implementation of move_to_and_click."""
        element.hover()
        element.click()

    def drag_and_drop(self, source: WebElementProtocol, target: WebElementProtocol) -> None:
        """
        Drag and drop from source element to target element.

        Uses Playwright's drag and drop functionality via JavaScript.

        Args:
            source: The element to drag
            target: The element to drop onto
        """
        self._drag_and_drop(self._unwrap_element(source), self._unwrap_element(target))

    def _drag_and_drop(self, source: ElementHandle, target: ElementHandle) -> None:
        """
        Internal implementation of drag and drop.

        Uses JavaScript to simulate drag and drop events.
        """
        self.page.evaluate(
            """
            (elements) => {
                const [source, target] = elements;
                const dataTransfer = new DataTransfer();
                const dragstart = new DragEvent('dragstart', { dataTransfer, bubbles: true });
                const dragover = new DragEvent('dragover', { dataTransfer, bubbles: true });
                const drop = new DragEvent('drop', { dataTransfer, bubbles: true });
                source.dispatchEvent(dragstart);
                target.dispatchEvent(dragover);
                target.dispatchEvent(drop);
            }
            """,
            [source, target],
        )

    def action_chains(self):
        """
        Return action chains object (for Playwright, returns None as not needed).

        Playwright handles actions differently than Selenium, so this method
        returns None to maintain API compatibility.

        Returns:
            None (Playwright doesn't use ActionChains pattern)
        """
        # Playwright doesn't use action chains - return a placeholder object
        # that indicates it exists but isn't used the same way
        return self

    def switch_to_frame(self, frame_reference: Union[str, int, ElementHandle, PlaywrightElement] = "frame"):
        """
        Switch to an iframe or frame.

        Playwright handles frames differently than Selenium - it doesn't have a "switch"
        concept. Instead, we store the frame reference so subsequent operations can
        use the appropriate frame context.

        Args:
            frame_reference: Can be:
                - str: frame name or id
                - int: frame index
                - ElementHandle: frame element
                - WebElementProtocol: PlaywrightElement wrapping a frame element

        Note: In Playwright, after calling this method, you should use the frame
        context for subsequent operations. This implementation updates the internal
        state to track the current frame.
        """
        if isinstance(frame_reference, str):
            # Find frame by name or id
            # Try as name attribute first
            frame = self.page.frame(name=frame_reference)
            if frame is None:
                # Try as frame locator by name attribute selector
                frame_locator = self.page.frame_locator(f"[name='{frame_reference}']")
                # Store the frame locator for future use
                self._current_frame = frame_locator
            else:
                self._current_frame = frame
        elif isinstance(frame_reference, int):
            # Get frame by index
            frames = self.page.frames
            if frame_reference < len(frames):
                self._current_frame = frames[frame_reference]
            else:
                raise ValueError(f"Frame index {frame_reference} out of range")
        elif isinstance(frame_reference, PlaywrightElement):
            # Unwrap PlaywrightElement to get ElementHandle, then get frame
            element_handle = self._unwrap_element(frame_reference)
            self._current_frame = element_handle.content_frame()
        else:
            # Assume it's an ElementHandle representing a frame
            # Get the content_frame from the element
            self._current_frame = frame_reference.content_frame()

    def switch_to_default_content(self):
        """
        Switch back to the default content (main page context).

        This exits any iframe/frame context and returns to the top-level page.
        """
        self._current_frame = None

    @property
    def _frame_or_page(self):
        """Get the current frame or page for operations."""
        return self._current_frame if hasattr(self, "_current_frame") and self._current_frame else self.page

    def execute_script(self, script: str, *args):
        """
        Execute JavaScript in the current browser context.

        Args:
            script: JavaScript code to execute
            *args: Arguments to pass to the script (accessible via arguments[0], arguments[1], etc.)

        Returns:
            The result of the script execution
        """
        # Playwright's evaluate() passes a single argument to the JS function
        # We need to make it look like Selenium's arguments object
        # The trick is to receive the array and make it available as 'arguments'
        wrapped_script = f"""
        (args) => {{
            const arguments = args || [];
            {script}
        }}
        """

        # Unwrap any PlaywrightElement wrappers to get ElementHandles
        unwrapped_args = [
            self._unwrap_element(arg) if isinstance(arg, (PlaywrightElement, WebElementProtocol)) else arg
            for arg in args
        ]

        if unwrapped_args:
            return self.page.evaluate(wrapped_script, unwrapped_args)
        else:
            return self.page.evaluate(wrapped_script, [])

    def set_local_storage(self, key: str, value: str) -> None:
        """
        Set a value in the browser's localStorage.

        Args:
            key: Storage key
            value: Value to store (will be JSON serialized)
        """
        self.execute_script(f"""window.localStorage.setItem("{key}", {value});""")

    def remove_local_storage(self, key: str) -> None:
        """
        Remove a key from the browser's localStorage.

        Args:
            key: Storage key to remove
        """
        self.execute_script(f"""window.localStorage.removeItem("{key}");""")

    def scroll_into_view(self, element: WebElementProtocol) -> None:
        """
        Scroll an element into view using JavaScript.

        Args:
            element: The element to scroll into view
        """
        self._scroll_into_view(self._unwrap_element(element))

    def _scroll_into_view(self, element: ElementHandle) -> None:
        """Internal implementation of scroll_into_view."""
        # Playwright has a built-in scroll_into_view_if_needed, but for consistency
        # with Selenium implementation, we'll use JavaScript
        self.execute_script("arguments[0].scrollIntoView(true);", element)

    def set_element_value(self, element: WebElementProtocol, value: str) -> None:
        """
        Set an element's value property directly using JavaScript.

        Args:
            element: The element to modify
            value: The value to set
        """
        self._set_element_value(self._unwrap_element(element), value)

    def _set_element_value(self, element: ElementHandle, value: str) -> None:
        """Internal implementation of set_element_value."""
        self.execute_script(f"arguments[0].value = '{value}';", element)

    def execute_script_click(self, element: WebElementProtocol) -> None:
        """
        Click an element using JavaScript.

        Args:
            element: The element to click
        """
        self._execute_script_click(self._unwrap_element(element))

    def _execute_script_click(self, element: ElementHandle) -> None:
        """Internal implementation of execute_script_click."""
        self.execute_script("arguments[0].click();", element)

    def get_cookies(self) -> list[Cookie]:
        """
        Get all cookies for the current domain.

        Returns:
            List of cookie dictionaries
        """
        # Playwright stores cookies in the browser context
        # Playwright returns list[playwright._impl._api_structures.Cookie] which is
        # structurally compatible with our Cookie TypedDict but mypy sees them as
        # invariant types. This is safe because both have the same keys at runtime.
        return self.page.context.cookies()  # type: ignore[return-value]

    def fill(self, form: WebElementProtocol, info: dict) -> None:
        """
        Fill form fields with provided data.

        Args:
            form: The form element
            info: Dictionary mapping field names/IDs to values
        """
        for key, value in info.items():
            try:
                # Try by name first
                input_element = form.find_element("name", key)
            except Exception:
                # Fall back to ID
                input_element = form.find_element("id", key)
            input_element.send_keys(value)

    def click_submit(self, form: WebElementProtocol) -> None:
        """
        Click the submit button on a form.

        Args:
            form: The form element
        """
        submit_button = form.find_element("css selector", "input[type='submit']")
        submit_button.click()

    def accept_alert(self) -> None:
        """
        Accept/confirm a browser alert dialog.

        Note: Playwright handles dialogs differently than Selenium.
        You typically need to set up dialog handlers before triggering the dialog.
        This implementation assumes a dialog handler is already in place.
        """

        # Playwright requires setting up event handlers for dialogs
        # This is a synchronous API, so we need to handle this differently
        # For now, we'll use a temporary handler that accepts dialogs
        def handle_dialog(dialog):
            dialog.accept()

        # Set up the handler
        self.page.once("dialog", handle_dialog)

    def prepend_timeout_message(
        self, timeout_exception: PlaywrightTimeoutException, message: str
    ) -> PlaywrightTimeoutException:
        """
        Prepend a custom message to a timeout exception.

        Args:
            timeout_exception: The original timeout exception
            message: Message to prepend

        Returns:
            New PlaywrightTimeoutException with prepended message
        """
        msg = message
        if hasattr(timeout_exception, "message") and timeout_exception.message:
            msg += f" {timeout_exception.message}"
        return PlaywrightTimeoutException(msg)

    def axe_eval(self, context: Optional[str] = None, write_to: Optional[str] = None) -> AxeResults:
        """
        Run axe-core accessibility tests on the current page.

        Args:
            context: Optional CSS selector to limit the scope of testing
            write_to: Optional file path to write results to

        Returns:
            AxeResults object with test results
        """
        if self.axe_skip:
            return NullAxeResults()

        # Load and inject axe-core script
        content = get_axe_script(self.axe_script_url)
        self.page.evaluate(content)

        if context is None and self._current_frame is not None:
            if isinstance(self._current_frame, Frame):
                context = f"iframe#{self._current_frame.name}"
            else:
                raise NotImplementedError("Playwright frame locators not yet supported for axe context")

        # Run axe with optional context
        # Playwright's evaluate() handles promises automatically
        if context:
            results = self.page.evaluate(f"axe.run({context!r})")
        else:
            results = self.page.evaluate("axe.run()")

        if write_to is not None:
            import json

            with open(write_to, "w") as f:
                json.dump(results, f, indent=2)

        return RealAxeResults(results)

    def save_screenshot(self, path: str) -> None:
        """
        Save a screenshot to the specified path.

        Args:
            path: File path where the screenshot should be saved
        """
        self.page.screenshot(path=path)

    def get_screenshot_as_png(self) -> bytes:
        """
        Capture a screenshot and return it as PNG bytes.

        Returns:
            PNG image data as bytes
        """
        return self.page.screenshot()

    def quit(self) -> None:
        """
        Clean up and close the driver/browser.

        This closes all windows/tabs and releases all system resources.
        The driver cannot be used after calling this method.
        """
        self._playwright_resources.browser.close()
        self._playwright_resources.playwright.stop()


__all__ = (
    "HasPlaywrightDriver",
    "PlaywrightResources",
    "PlaywrightTimeoutException",
)
