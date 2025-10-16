"""Protocol defining the common interface for HasDriver and HasPlaywrightDriver.

This Protocol captures the ~60+ methods that both implementations provide,
allowing NavigatesGalaxy to work with either backend via composition.
"""

from abc import abstractmethod
from typing import (
    Any,
    Callable,
    Generic,
    Literal,
    Optional,
    Protocol,
    TypedDict,
    TypeVar,
    Union,
)

from galaxy.navigation.components import Target
from .axe_results import AxeResults
from .web_element_protocol import WebElementProtocol

# Type for element locators - can be either a Target or a Selenium-style (locator_type, value) tuple
ElementLocatorTuple = tuple[str, str]  # e.g., ("css selector", "#id") or ("id", "test")
HasElementLocator = Union[Target, ElementLocatorTuple]


class Cookie(TypedDict, total=False):
    """Cookie dictionary structure compatible with both Selenium and Playwright."""

    name: str
    value: str
    domain: str
    path: str
    expires: float
    httpOnly: bool
    secure: bool
    sameSite: Literal["Lax", "None", "Strict"]


BackendType = Literal["selenium", "playwright"]
WaitTypeT = TypeVar("WaitTypeT", contravariant=True)
TimeoutCallback = Callable[[Optional[WaitTypeT]], float]


def fixed_timeout_handler(timeout: float) -> TimeoutCallback:
    """Return a fixed timeout callback for simple timeout_handler impls."""

    def callback(wait_type=None) -> float:
        return timeout

    return callback


class HasDriverProtocol(Protocol, Generic[WaitTypeT]):
    """
    Protocol defining the driver abstraction interface.

    Both HasDriver (Selenium) and HasPlaywrightDriver (Playwright) implement
    this protocol, allowing NavigatesGalaxy to work with either backend.

    This protocol includes:
    - Backend identification (backend_type)
    - Navigation methods (navigate_to, re_get_with_query_params, current_url)
    - Element finding (find_element_by_*, find_elements*)
    - Wait methods (wait_for_*, wait_for_*_visible, etc.)
    - Interaction methods (click_*, hover, drag_and_drop, etc.)
    - Assertion methods (assert_*, selector_is_displayed, etc.)
    - JavaScript execution (execute_script, set_element_value, etc.)
    - Frame switching (switch_to_frame, switch_to_default_content)
    - Storage & cookies (set_local_storage, get_cookies, etc.)
    - Accessibility (axe_eval)
    """

    # Backend identification
    @property
    @abstractmethod
    def backend_type(self) -> BackendType:
        """Identify which backend implementation this is."""
        ...

    # Core timeout management
    @property
    @abstractmethod
    def timeout_handler(self) -> TimeoutCallback:
        """Get timeout handler for application specific wait types."""
        ...

    @abstractmethod
    def wait(self, timeout=..., wait_type: Optional[WaitTypeT] = None, **kwds):
        """Create a wait object with the specified timeout."""
        ...

    # Navigation
    @property
    @abstractmethod
    def current_url(self) -> str:
        """Get the current page URL."""
        ...

    @property
    @abstractmethod
    def page_source(self) -> str:
        """Get the HTML source of the current page."""
        ...

    @property
    @abstractmethod
    def page_title(self) -> str:
        """Get the title of the current page."""
        ...

    @abstractmethod
    def navigate_to(self, url: str) -> None:
        """Navigate to the specified URL."""
        ...

    @abstractmethod
    def re_get_with_query_params(self, params_str: str):
        """Navigate to current URL with additional query parameters."""
        ...

    # Element finding - by locator type
    @abstractmethod
    def find_element_by_id(self, id: str, element: Optional[Any] = None) -> WebElementProtocol:
        """Find element by ID attribute."""
        ...

    @abstractmethod
    def find_element_by_selector(self, selector: str, element: Optional[Any] = None) -> WebElementProtocol:
        """Find element by CSS selector."""
        ...

    @abstractmethod
    def find_element_by_xpath(self, xpath: str, element: Optional[Any] = None) -> WebElementProtocol:
        """Find element by XPath expression."""
        ...

    @abstractmethod
    def find_element_by_link_text(self, text: str, element: Optional[Any] = None) -> WebElementProtocol:
        """Find link element by visible text."""
        ...

    @abstractmethod
    def find_elements_by_selector(self, selector: str, element: Optional[Any] = None) -> list[WebElementProtocol]:
        """Find all elements matching CSS selector."""
        ...

    @abstractmethod
    def find_elements(self, selector_template: Target) -> list[WebElementProtocol]:
        """Find all elements matching the Target selector template."""
        ...

    @abstractmethod
    def find_element(self, selector_template: HasElementLocator) -> WebElementProtocol:
        """
        Find first element matching the selector template (no waiting).

        Args:
            selector_template: Either a Target or a (locator_type, value) tuple
        """
        ...

    # Wait methods - presence
    @abstractmethod
    def wait_for_xpath(self, xpath: str, **kwds) -> Any:
        """Wait for element matching XPath to be present in DOM."""
        ...

    @abstractmethod
    def wait_for_selector(self, selector: str, **kwds) -> Any:
        """Wait for element matching CSS selector to be present in DOM."""
        ...

    @abstractmethod
    def wait_for_present(self, selector_template: Target, **kwds) -> Any:
        """Wait for element matching Target to be present in DOM."""
        ...

    @abstractmethod
    def wait_for_id(self, id: str, **kwds) -> Any:
        """Wait for element with ID to be present in DOM."""
        ...

    # Wait methods - visibility
    @abstractmethod
    def wait_for_xpath_visible(self, xpath: str, **kwds) -> Any:
        """Wait for element matching XPath to be visible."""
        ...

    @abstractmethod
    def wait_for_selector_visible(self, selector: str, **kwds) -> Any:
        """Wait for element matching CSS selector to be visible."""
        ...

    @abstractmethod
    def wait_for_visible(self, selector_template: Target, **kwds) -> Any:
        """Wait for element matching Target to be visible."""
        ...

    # Wait methods - clickable
    @abstractmethod
    def wait_for_selector_clickable(self, selector: str, **kwds) -> Any:
        """Wait for element matching CSS selector to be clickable."""
        ...

    @abstractmethod
    def wait_for_clickable(self, selector_template: Target, **kwds) -> Any:
        """Wait for element matching Target to be clickable."""
        ...

    # Wait methods - absence/hidden
    @abstractmethod
    def wait_for_selector_absent(self, selector: str, **kwds) -> Any:
        """Wait for element matching CSS selector to be absent from DOM."""
        ...

    @abstractmethod
    def wait_for_absent(self, selector_template: Target, **kwds) -> Any:
        """Wait for element matching Target to be absent from DOM."""
        ...

    @abstractmethod
    def wait_for_selector_absent_or_hidden(self, selector: str, **kwds) -> Any:
        """Wait for element matching CSS selector to be absent or hidden."""
        ...

    @abstractmethod
    def wait_for_absent_or_hidden(self, selector_template: Target, **kwds) -> Any:
        """Wait for element matching Target to be absent or hidden."""
        ...

    # Wait methods - count
    @abstractmethod
    def wait_for_element_count_of_at_least(self, selector_template: Target, n: int, **kwds) -> Any:
        """Wait for at least n elements matching Target to be present."""
        ...

    # Wait and interact
    @abstractmethod
    def wait_for_and_click(self, selector_template: Target, **kwds) -> Any:
        """Wait for element to be clickable and click it."""
        ...

    @abstractmethod
    def wait_for_and_double_click(self, selector_template: Target, **kwds) -> Any:
        """Wait for element to be clickable and double-click it."""
        ...

    # Visibility checks
    @abstractmethod
    def selector_is_displayed(self, selector: str) -> bool:
        """Check if element matching CSS selector is displayed."""
        ...

    @abstractmethod
    def is_displayed(self, selector_template: Target) -> bool:
        """Check if element matching Target is displayed."""
        ...

    @abstractmethod
    def element_absent(self, selector_template: Target) -> bool:
        """Check if element matching Target is absent from DOM."""
        ...

    # Assertions
    @abstractmethod
    def assert_xpath(self, xpath: str):
        """Assert element matching XPath is present."""
        ...

    @abstractmethod
    def assert_selector(self, selector: str):
        """Assert element matching CSS selector is present."""
        ...

    @abstractmethod
    def assert_selector_absent(self, selector: str):
        """Assert element matching CSS selector is absent."""
        ...

    @abstractmethod
    def assert_selector_absent_or_hidden(self, selector: str):
        """Assert element matching CSS selector is absent or hidden."""
        ...

    @abstractmethod
    def assert_absent(self, selector_template: Target) -> None:
        """Assert element matching Target is absent."""
        ...

    @abstractmethod
    def assert_absent_or_hidden(self, selector_template: Target):
        """Assert element matching Target is absent or hidden."""
        ...

    @abstractmethod
    def assert_disabled(self, selector_template: Target):
        """Assert element matching Target is disabled."""
        ...

    @abstractmethod
    def assert_absent_or_hidden_after_transitions(self, selector_template: Target, **kwds) -> None:
        """Assert element is absent or hidden, retrying during transitions."""
        ...

    # Click methods
    @abstractmethod
    def click(self, selector_template: Target):
        """Click element matching Target."""
        ...

    @abstractmethod
    def click_xpath(self, xpath: str):
        """Click element matching XPath."""
        ...

    @abstractmethod
    def click_selector(self, selector: str):
        """Click element matching CSS selector."""
        ...

    @abstractmethod
    def click_label(self, text: str):
        """Click link with visible text."""
        ...

    # Mouse interactions
    @abstractmethod
    def hover(self, element: WebElementProtocol) -> None:
        """Hover mouse over element."""
        ...

    @abstractmethod
    def move_to_and_click(self, element: WebElementProtocol) -> None:
        """Move mouse to element and click."""
        ...

    @abstractmethod
    def drag_and_drop(self, source: WebElementProtocol, target: WebElementProtocol) -> None:
        """Drag source element and drop on target element."""
        ...

    @abstractmethod
    def double_click(self, element: WebElementProtocol) -> None:
        """Double-click element."""
        ...

    @abstractmethod
    def action_chains(self):
        """Get action chains object for complex interactions."""
        ...

    # Keyboard interactions
    @abstractmethod
    def send_enter(self, element: Optional[WebElementProtocol] = None):
        """Send ENTER key to element or active element."""
        ...

    @abstractmethod
    def send_escape(self, element: Optional[WebElementProtocol] = None):
        """Send ESCAPE key to element or active element."""
        ...

    @abstractmethod
    def send_backspace(self, element: Optional[WebElementProtocol] = None):
        """Send BACKSPACE key to element or active element."""
        ...

    @abstractmethod
    def aggressive_clear(self, element: WebElementProtocol) -> None:
        """Clear input element value using JavaScript and backspaces (for when .clear() doesn't work)."""
        ...

    # Form interactions
    @abstractmethod
    def fill(self, form: WebElementProtocol, info: dict):
        """Fill form with provided data."""
        ...

    @abstractmethod
    def click_submit(self, form: WebElementProtocol):
        """Click submit button in form."""
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    def select_by_value(self, selector_template: HasElementLocator, value: str) -> None:
        """
        Select an option from a <select> element by its value attribute.

        Args:
            selector_template: Either a Target or a (locator_type, value) tuple for the select element
            value: The value attribute of the option to select
        """
        ...

    # Frame switching
    @abstractmethod
    def switch_to_frame(self, frame_reference: Union[str, int, Any] = "frame"):
        """Switch to iframe by name, id, index, or element."""
        ...

    @abstractmethod
    def switch_to_default_content(self):
        """Switch back to main page content from iframe."""
        ...

    # JavaScript execution
    @abstractmethod
    def execute_script(self, script: str, *args):
        """Execute JavaScript in the browser."""
        ...

    @abstractmethod
    def execute_script_click(self, element: WebElementProtocol) -> None:
        """Click element using JavaScript."""
        ...

    @abstractmethod
    def set_element_value(self, element: WebElementProtocol, value: str) -> None:
        """Set input element value using JavaScript."""
        ...

    @abstractmethod
    def scroll_into_view(self, element: WebElementProtocol) -> None:
        """Scroll element into viewport."""
        ...

    # Storage and cookies
    @abstractmethod
    def set_local_storage(self, key: str, value: Union[str, float]) -> None:
        """Set localStorage item."""
        ...

    @abstractmethod
    def remove_local_storage(self, key: str) -> None:
        """Remove localStorage item."""
        ...

    @abstractmethod
    def get_cookies(self) -> list[Cookie]:
        """Get all browser cookies."""
        ...

    # Alert handling
    @abstractmethod
    def accept_alert(self):
        """Accept browser alert dialog."""
        ...

    # Accessibility
    @abstractmethod
    def axe_eval(self, context: Optional[str] = None, write_to: Optional[str] = None) -> AxeResults:
        """Run axe-core accessibility tests."""
        ...

    # Screenshots
    @abstractmethod
    def save_screenshot(self, path: str) -> None:
        """Save a screenshot to the specified path."""
        ...

    @abstractmethod
    def get_screenshot_as_png(self) -> bytes:
        """
        Capture a screenshot and return it as PNG bytes.

        Returns:
            PNG image data as bytes
        """
        ...

    # Timeout utilities
    @abstractmethod
    def _timeout_message(self, on_str: str) -> str:
        """
        Generate a timeout error message.

        Args:
            on_str: Description of what was being waited on

        Returns:
            Formatted timeout message string
        """
        ...

    @abstractmethod
    def prepend_timeout_message(
        self,
        timeout_exception: Exception,
        message: str,
    ) -> Exception:
        """Add context to timeout exception message."""
        ...

    # Lifecycle management
    @abstractmethod
    def quit(self) -> None:
        """
        Clean up and close the driver/browser.

        This closes all windows/tabs and releases all system resources.
        The driver cannot be used after calling this method.
        """
        ...


__all__ = (
    "HasDriverProtocol",
    "BackendType",
    "TimeoutCallback",
    "WaitTypeT",
    "Cookie",
    "fixed_timeout_handler",
    "HasElementLocator",
    "ElementLocatorTuple",
)
