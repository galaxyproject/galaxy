"""Proxy base class for delegating driver operations to a HasDriverProtocol implementation.

This module provides HasDriverProxy, a mixin that implements the driver
abstraction interface by delegating all operations to a pluggable implementation,
and HasDriverProxyImpl, a concrete base class with constructor.
NavigatesGalaxy extends this proxy to enable runtime backend selection.
"""

from abc import (
    ABC,
    abstractmethod,
)
from typing import (
    Any,
    Generic,
    Optional,
    Union,
)

from galaxy.navigation.components import Target
from .axe_results import AxeResults
from .has_driver_protocol import (
    BackendType,
    Cookie,
    HasDriverProtocol,
    HasElementLocator,
    TimeoutCallback,
    WaitTypeT,
)
from .web_element_protocol import WebElementProtocol


class HasDriverProxy(ABC, Generic[WaitTypeT]):
    """
    Proxy mixin that delegates all driver operations to an implementation.

    This mixin provides composition over inheritance - it requires subclasses to
    implement _driver_impl as a property that returns a HasDriverProtocol implementation.
    All driver operations are forwarded to this implementation.

    This is an abstract base class. Subclasses must implement _driver_impl as a property:

    Usage as direct subclass:
        class MyClass(HasDriverProxy):
            def __init__(self):
                self._impl = create_driver()  # Store in private attribute

            @property
            def _driver_impl(self):
                return self._impl  # Return via property

            def my_custom_method(self):
                self.click_selector("#my-button")

    Usage with HasDriverProxyImpl:
        class MyClass(HasDriverProxyImpl):
            def __init__(self):
                driver_impl = create_driver()
                super().__init__(driver_impl)  # Stores and provides via property

    Attributes:
        _driver_impl: Abstract property that must return a HasDriverProtocol implementation
    """

    @property
    @abstractmethod
    def _driver_impl(self) -> HasDriverProtocol[WaitTypeT]:
        """Return the HasDriverProtocol implementation to delegate to.

        Subclasses must implement this property to provide the driver implementation.
        """
        ...

    @property
    def backend_type(self) -> BackendType:
        """Return the backend type of the driver implementation."""
        return self._driver_impl.backend_type

    # Core timeout management

    @property
    def timeout_handler(self) -> TimeoutCallback:
        """Get timeout handler for application specific wait types."""
        return self._driver_impl.timeout_handler

    def wait(self, timeout=..., wait_type: Optional[WaitTypeT] = None, **kwds):
        """Create a wait object with the specified timeout."""
        return self._driver_impl.wait(timeout, wait_type=wait_type, **kwds)

    # Navigation

    @property
    def current_url(self) -> str:
        """Get the current page URL."""
        return self._driver_impl.current_url

    @property
    def page_source(self) -> str:
        """Get the HTML source of the current page."""
        return self._driver_impl.page_source

    @property
    def page_title(self) -> str:
        """Get the title of the current page."""
        return self._driver_impl.page_title

    def navigate_to(self, url: str) -> None:
        """Navigate to the specified URL."""
        self._driver_impl.navigate_to(url)

    def re_get_with_query_params(self, params_str: str):
        """Navigate to current URL with additional query parameters."""
        return self._driver_impl.re_get_with_query_params(params_str)

    # Element finding - by locator type

    def find_element_by_id(self, id: str, element: Optional[Any] = None) -> WebElementProtocol:
        """Find element by ID attribute."""
        return self._driver_impl.find_element_by_id(id, element)

    def find_element_by_selector(self, selector: str, element: Optional[Any] = None) -> WebElementProtocol:
        """Find element by CSS selector."""
        return self._driver_impl.find_element_by_selector(selector, element)

    def find_element_by_xpath(self, xpath: str, element: Optional[Any] = None) -> WebElementProtocol:
        """Find element by XPath expression."""
        return self._driver_impl.find_element_by_xpath(xpath, element)

    def find_element_by_link_text(self, text: str, element: Optional[Any] = None) -> WebElementProtocol:
        """Find link element by visible text."""
        return self._driver_impl.find_element_by_link_text(text, element)

    def find_elements_by_selector(self, selector: str, element: Optional[Any] = None) -> list[WebElementProtocol]:
        """Find all elements matching CSS selector."""
        return self._driver_impl.find_elements_by_selector(selector, element)

    def find_elements(self, selector_template: Target) -> list[WebElementProtocol]:
        """Find all elements matching the Target selector template."""
        return self._driver_impl.find_elements(selector_template)

    def find_element(self, selector_template: HasElementLocator) -> WebElementProtocol:
        """
        Find first element matching selector template (no waiting).

        Args:
            selector_template: Either a Target or a (locator_type, value) tuple
        """
        return self._driver_impl.find_element(selector_template)

    # Wait methods - presence

    def wait_for_xpath(self, xpath: str, **kwds) -> Any:
        """Wait for element matching XPath to be present in DOM."""
        return self._driver_impl.wait_for_xpath(xpath, **kwds)

    def wait_for_selector(self, selector: str, **kwds) -> Any:
        """Wait for element matching CSS selector to be present in DOM."""
        return self._driver_impl.wait_for_selector(selector, **kwds)

    def wait_for_present(self, selector_template: Target, **kwds) -> Any:
        """Wait for element matching Target to be present in DOM."""
        return self._driver_impl.wait_for_present(selector_template, **kwds)

    def wait_for_id(self, id: str, **kwds) -> Any:
        """Wait for element with ID to be present in DOM."""
        return self._driver_impl.wait_for_id(id, **kwds)

    # Wait methods - visibility

    def wait_for_xpath_visible(self, xpath: str, **kwds) -> Any:
        """Wait for element matching XPath to be visible."""
        return self._driver_impl.wait_for_xpath_visible(xpath, **kwds)

    def wait_for_selector_visible(self, selector: str, **kwds) -> Any:
        """Wait for element matching CSS selector to be visible."""
        return self._driver_impl.wait_for_selector_visible(selector, **kwds)

    def wait_for_visible(self, selector_template: Target, **kwds) -> Any:
        """Wait for element matching Target to be visible."""
        return self._driver_impl.wait_for_visible(selector_template, **kwds)

    # Wait methods - clickable

    def wait_for_selector_clickable(self, selector: str, **kwds) -> Any:
        """Wait for element matching CSS selector to be clickable."""
        return self._driver_impl.wait_for_selector_clickable(selector, **kwds)

    def wait_for_clickable(self, selector_template: Target, **kwds) -> Any:
        """Wait for element matching Target to be clickable."""
        return self._driver_impl.wait_for_clickable(selector_template, **kwds)

    # Wait methods - absence/hidden

    def wait_for_selector_absent(self, selector: str, **kwds) -> Any:
        """Wait for element matching CSS selector to be absent from DOM."""
        return self._driver_impl.wait_for_selector_absent(selector, **kwds)

    def wait_for_absent(self, selector_template: Target, **kwds) -> Any:
        """Wait for element matching Target to be absent from DOM."""
        return self._driver_impl.wait_for_absent(selector_template, **kwds)

    def wait_for_selector_absent_or_hidden(self, selector: str, **kwds) -> Any:
        """Wait for element matching CSS selector to be absent or hidden."""
        return self._driver_impl.wait_for_selector_absent_or_hidden(selector, **kwds)

    def wait_for_absent_or_hidden(self, selector_template: Target, **kwds) -> Any:
        """Wait for element matching Target to be absent or hidden."""
        return self._driver_impl.wait_for_absent_or_hidden(selector_template, **kwds)

    # Wait methods - count

    def wait_for_element_count_of_at_least(self, selector_template: Target, n: int, **kwds) -> Any:
        """Wait for at least n elements matching Target to be present."""
        return self._driver_impl.wait_for_element_count_of_at_least(selector_template, n, **kwds)

    # Wait and interact

    def wait_for_and_click(self, selector_template: Target, **kwds) -> Any:
        """Wait for element to be clickable and click it."""
        return self._driver_impl.wait_for_and_click(selector_template, **kwds)

    def wait_for_and_double_click(self, selector_template: Target, **kwds) -> Any:
        """Wait for element to be clickable and double-click it."""
        return self._driver_impl.wait_for_and_double_click(selector_template, **kwds)

    # Custom wait abstraction
    def _wait_on_custom(self, condition_func, message: str, **kwds) -> Any:
        """Wait on custom condition function."""
        return self._driver_impl._wait_on_custom(condition_func, message, **kwds)

    # Visibility checks

    def selector_is_displayed(self, selector: str) -> bool:
        """Check if element matching CSS selector is displayed."""
        return self._driver_impl.selector_is_displayed(selector)

    def is_displayed(self, selector_template: Target) -> bool:
        """Check if element matching Target is displayed."""
        return self._driver_impl.is_displayed(selector_template)

    def element_absent(self, selector_template: Target) -> bool:
        """Check if element matching Target is absent from DOM."""
        return self._driver_impl.element_absent(selector_template)

    # Assertions

    def assert_xpath(self, xpath: str):
        """Assert element matching XPath is present."""
        return self._driver_impl.assert_xpath(xpath)

    def assert_selector(self, selector: str):
        """Assert element matching CSS selector is present."""
        return self._driver_impl.assert_selector(selector)

    def assert_selector_absent(self, selector: str):
        """Assert element matching CSS selector is absent."""
        return self._driver_impl.assert_selector_absent(selector)

    def assert_selector_absent_or_hidden(self, selector: str):
        """Assert element matching CSS selector is absent or hidden."""
        return self._driver_impl.assert_selector_absent_or_hidden(selector)

    def assert_absent(self, selector_template: Target) -> None:
        """Assert element matching Target is absent."""
        self._driver_impl.assert_absent(selector_template)

    def assert_absent_or_hidden(self, selector_template: Target):
        """Assert element matching Target is absent or hidden."""
        return self._driver_impl.assert_absent_or_hidden(selector_template)

    def assert_disabled(self, selector_template: Target):
        """Assert element matching Target is disabled."""
        return self._driver_impl.assert_disabled(selector_template)

    def assert_absent_or_hidden_after_transitions(self, selector_template: Target, **kwds) -> None:
        """Assert element is absent or hidden, retrying during transitions."""
        self._driver_impl.assert_absent_or_hidden_after_transitions(selector_template, **kwds)

    # Click methods

    def click(self, selector_template: Target):
        """Click element matching Target."""
        return self._driver_impl.click(selector_template)

    def click_xpath(self, xpath: str):
        """Click element matching XPath."""
        return self._driver_impl.click_xpath(xpath)

    def click_selector(self, selector: str):
        """Click element matching CSS selector."""
        return self._driver_impl.click_selector(selector)

    def click_label(self, text: str):
        """Click link with visible text."""
        return self._driver_impl.click_label(text)

    # Mouse interactions

    def hover(self, element: WebElementProtocol) -> None:
        """Hover mouse over element."""
        self._driver_impl.hover(element)

    def move_to_and_click(self, element: WebElementProtocol) -> None:
        """Move mouse to element and click."""
        self._driver_impl.move_to_and_click(element)

    def drag_and_drop(self, source: WebElementProtocol, target: WebElementProtocol) -> None:
        """Drag source element and drop on target element."""
        self._driver_impl.drag_and_drop(source, target)

    def double_click(self, element: WebElementProtocol) -> None:
        """Double-click element."""
        self._driver_impl.double_click(element)

    def action_chains(self):
        """Get action chains object for complex interactions."""
        return self._driver_impl.action_chains()

    # Keyboard interactions

    def send_enter(self, element: Optional[WebElementProtocol] = None):
        """Send ENTER key to element or active element."""
        return self._driver_impl.send_enter(element)

    def send_escape(self, element: Optional[WebElementProtocol] = None):
        """Send ESCAPE key to element or active element."""
        return self._driver_impl.send_escape(element)

    def send_backspace(self, element: Optional[WebElementProtocol] = None):
        """Send BACKSPACE key to element or active element."""
        return self._driver_impl.send_backspace(element)

    def aggressive_clear(self, element: WebElementProtocol) -> None:
        """Clear input element value using JavaScript and backspaces (for when .clear() doesn't work)."""
        self._driver_impl.aggressive_clear(element)

    # Form interactions

    def fill(self, form: WebElementProtocol, info: dict):
        """Fill form with provided data."""
        return self._driver_impl.fill(form, info)

    def click_submit(self, form: WebElementProtocol):
        """Click submit button in form."""
        return self._driver_impl.click_submit(form)

    def get_input_value(self, element: WebElementProtocol) -> str:
        """
        Get the value of an input element.

        This provides a unified interface for getting input values across both
        Selenium and Playwright backends.

        Args:
            element: The input element to get the value from

        Returns:
            The current value of the input element, or empty string if no value
        """
        return self._driver_impl.get_input_value(element)

    def select_by_value(self, selector_template: HasElementLocator, value: str) -> None:
        """
        Select an option from a <select> element by its value attribute.

        Args:
            selector_template: Either a Target or a (locator_type, value) tuple for the select element
            value: The value attribute of the option to select
        """
        return self._driver_impl.select_by_value(selector_template, value)

    # Frame switching

    def switch_to_frame(self, frame_reference: Union[str, int, Any] = "frame"):
        """Switch to iframe by name, id, index, or element."""
        return self._driver_impl.switch_to_frame(frame_reference)

    def switch_to_default_content(self):
        """Switch back to main page content from iframe."""
        return self._driver_impl.switch_to_default_content()

    # JavaScript execution

    def execute_script(self, script: str, *args):
        """Execute JavaScript in the browser."""
        return self._driver_impl.execute_script(script, *args)

    def execute_script_click(self, element: WebElementProtocol) -> None:
        """Click element using JavaScript."""
        self._driver_impl.execute_script_click(element)

    def set_element_value(self, element: WebElementProtocol, value: str) -> None:
        """Set input element value using JavaScript."""
        self._driver_impl.set_element_value(element, value)

    def scroll_into_view(self, element: WebElementProtocol) -> None:
        """Scroll element into viewport."""
        self._driver_impl.scroll_into_view(element)

    # Storage and cookies

    def set_local_storage(self, key: str, value: Union[str, float]) -> None:
        """Set localStorage item."""
        self._driver_impl.set_local_storage(key, value)

    def remove_local_storage(self, key: str) -> None:
        """Remove localStorage item."""
        self._driver_impl.remove_local_storage(key)

    def get_cookies(self) -> list[Cookie]:
        """Get all browser cookies."""
        return self._driver_impl.get_cookies()

    # Alert handling

    def accept_alert(self):
        """Accept browser alert dialog."""
        return self._driver_impl.accept_alert()

    # Accessibility

    def axe_eval(self, context: Optional[str] = None, write_to: Optional[str] = None) -> AxeResults:
        """Run axe-core accessibility tests."""
        return self._driver_impl.axe_eval(context, write_to)

    # Screenshots

    def save_screenshot(self, path: str) -> None:
        """Save a screenshot to the specified path."""
        self._driver_impl.save_screenshot(path)

    def get_screenshot_as_png(self) -> bytes:
        """
        Capture a screenshot and return it as PNG bytes.

        Returns:
            PNG image data as bytes
        """
        return self._driver_impl.get_screenshot_as_png()

    # Timeout utilities

    def _timeout_message(self, on_str: str) -> str:
        """
        Generate a timeout error message.

        Args:
            on_str: Description of what was being waited on

        Returns:
            Formatted timeout message string
        """
        return self._driver_impl._timeout_message(on_str)

    def prepend_timeout_message(self, timeout_exception: Exception, message: str) -> Exception:
        """Add context to timeout exception message."""
        return self._driver_impl.prepend_timeout_message(timeout_exception, message)

    # Cleanup
    def close(self) -> None:
        """Close the current browser/page."""
        self._driver_impl.close()

    def quit(self) -> None:
        """Quit the driver and clean up resources."""
        self._driver_impl.quit()


class HasDriverProxyImpl(HasDriverProxy[WaitTypeT], Generic[WaitTypeT]):
    """
    Concrete implementation of HasDriverProxy with a constructor.

    This class provides the constructor that accepts and stores a driver implementation,
    then provides it via the _driver_impl property.

    Use this as a base class when you can directly pass the driver implementation
    to the constructor.

    Usage:
        class MyClass(HasDriverProxyImpl):
            def __init__(self, config):
                driver_impl = create_driver_from_config(config)
                super().__init__(driver_impl)

            def my_custom_method(self):
                self.click_selector("#my-button")
    """

    def __init__(self, driver_impl: HasDriverProtocol[WaitTypeT]):
        """
        Initialize the proxy with a driver implementation.

        Args:
            driver_impl: An object implementing HasDriverProtocol (HasDriver or HasPlaywrightDriver)
        """
        self.__driver_impl_value = driver_impl

    @property
    def _driver_impl(self) -> HasDriverProtocol[WaitTypeT]:
        """Return the stored driver implementation."""
        return self.__driver_impl_value


__all__ = ("HasDriverProxy", "HasDriverProxyImpl")
