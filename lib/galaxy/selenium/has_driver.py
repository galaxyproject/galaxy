"""A mixin to extend a class that has self.driver with higher-level constructs.

This should be mixed into classes with a self.driver and self.default_timeout
attribute.
"""

import abc
import threading
from contextlib import contextmanager
from typing import (
    cast,
    Generic,
    Literal,
    Optional,
    Union,
)

from axe_selenium_python import Axe
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException as SeleniumTimeoutException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from seletools.actions import drag_and_drop as seletools_drag_and_drop

from galaxy.navigation.components import Target
from galaxy.util import requests
from .axe_results import (
    AxeResults,
    NullAxeResults,
    RealAxeResults,
)
from .has_driver_protocol import (
    Cookie,
    HasElementLocator,
    TimeoutCallback,
    WaitTypeT,
)
from .wait_methods_mixin import WaitMethodsMixin
from .web_element_protocol import WebElementProtocol

UNSPECIFIED_TIMEOUT = object()

HasFindElement = Union[WebDriver, WebElement]
DEFAULT_AXE_SCRIPT_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.7.1/axe.min.js"
AXE_SCRIPT_HASH: dict[str, str] = {}
AXE_SCRIPT_HASH_LOCK = threading.Lock()


def get_axe_script(script_url: str) -> str:
    with AXE_SCRIPT_HASH_LOCK:
        if script_url not in AXE_SCRIPT_HASH:
            content = requests.get(script_url).text
            AXE_SCRIPT_HASH[script_url] = content

    return AXE_SCRIPT_HASH[script_url]


def _webelement_to_protocol(element: WebElement) -> WebElementProtocol:
    """
    Convert Selenium WebElement to WebElementProtocol type.

    Selenium's WebElement satisfies WebElementProtocol at runtime, but mypy
    doesn't recognize this because:
    1. WebElement.find_element() has parameters typed as (by: Any, value: Any)
       while our protocol requires (by: str, value: str | None)
    2. WebElement.find_element() returns WebElement instead of WebElementProtocol

    Since WebElement actually implements all required protocol methods correctly
    at runtime, this cast is safe.
    """
    return element  # type: ignore[return-value]


def _webelements_to_protocol(elements: list[WebElement]) -> list[WebElementProtocol]:
    """
    Convert list of Selenium WebElements to list of WebElementProtocol.

    See _webelement_to_protocol for why this type conversion is necessary.
    """
    return elements  # type: ignore[return-value]


def _cookies_to_typed(cookies: list[dict]) -> list[Cookie]:
    """
    Convert Selenium's list[dict] cookies to list[Cookie].

    Selenium's get_cookies() returns list[dict[Any, Any]], but the actual
    dictionaries at runtime contain the correct Cookie keys. We use a TypedDict
    to provide better type safety for cookie access. This cast is safe because
    Selenium's cookie dictionaries contain all the keys defined in Cookie.
    """
    return cookies  # type: ignore[return-value]


class TimeoutMessageMixin:
    """Mixin providing timeout message formatting for driver abstractions."""

    def _timeout_message(self, on_str: str) -> str:
        """
        Generate a timeout error message.

        Args:
            on_str: Description of what was being waited on

        Returns:
            Formatted timeout message string
        """
        return f"Timeout waiting on {on_str}."


class HasDriver(TimeoutMessageMixin, WaitMethodsMixin, Generic[WaitTypeT]):
    by: type[By] = By
    keys: type[Keys] = Keys
    driver: WebDriver
    axe_script_url: str = DEFAULT_AXE_SCRIPT_URL
    axe_skip: bool = False

    @property
    def backend_type(self) -> Literal["selenium", "playwright"]:
        """Identify this as the Selenium backend implementation."""
        return "selenium"

    @property
    def current_url(self) -> str:
        """
        Get the current page URL.

        Returns:
            The current URL
        """
        return self.driver.current_url

    @property
    def page_source(self) -> str:
        """
        Get the HTML source of the current page.

        Returns:
            The page HTML as a string
        """
        return self.driver.page_source

    @property
    def page_title(self) -> str:
        """
        Get the title of the current page.

        Returns:
            The page title as a string
        """
        return self.driver.title

    def navigate_to(self, url: str) -> None:
        """
        Navigate to a URL.

        Args:
            url: The URL to navigate to
        """
        self.driver.get(url)

    def re_get_with_query_params(self, params_str: str):
        driver = self.driver
        new_url = driver.current_url
        if "?" not in new_url:
            new_url += "?"
        new_url += params_str
        driver.get(new_url)

    def assert_xpath(self, xpath: str):
        assert self.driver.find_element(By.XPATH, xpath)

    def assert_selector(self, selector: str):
        assert self.driver.find_element(By.CSS_SELECTOR, selector)

    def assert_selector_absent_or_hidden(self, selector: str):
        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
        for element in elements:
            assert not element.is_displayed()

    def assert_absent_or_hidden(self, selector_template: Target):
        elements = self.find_elements(selector_template)
        for element in elements:
            assert not element.is_displayed()

    def assert_disabled(self, selector_template: Target):
        elements = self.find_elements(selector_template)
        assert len(elements) > 0
        for element in elements:
            assert not element.is_enabled()

    def selector_is_displayed(self, selector: str):
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        return element.is_displayed()

    def is_displayed(self, selector_template: Target) -> bool:
        element = self.driver.find_element(*selector_template.element_locator)
        return element.is_displayed()

    def assert_selector_absent(self, selector: str):
        assert len(self.driver.find_elements(By.CSS_SELECTOR, selector)) == 0

    def find_elements(self, selector_template: Target) -> list[WebElementProtocol]:
        return _webelements_to_protocol(self.driver.find_elements(*selector_template.element_locator))

    def find_element(self, selector_template: HasElementLocator) -> WebElementProtocol:
        """
        Find first element matching selector template (no waiting).

        Args:
            selector_template: Either a Target or a (locator_type, value) tuple
        """
        # Dispatch on input type
        if isinstance(selector_template, Target):
            locator = selector_template.element_locator
        else:
            # It's a tuple (locator_type, value)
            locator = selector_template
        return _webelement_to_protocol(self.driver.find_element(*locator))

    def assert_absent(self, selector_template: Target) -> None:
        elements = self.find_elements(selector_template)
        if len(elements) != 0:
            description = selector_template.description
            any_displayed = False
            for element in elements:
                any_displayed = any_displayed or element.is_displayed()
            msg = f"Expected DOM elements [{elements}] to be empty for selector target {description} - any actually displayed? [{any_displayed}]"
            raise AssertionError(msg)

    def element_absent(self, selector_template: Target) -> bool:
        return len(self.find_elements(selector_template)) == 0

    def switch_to_frame(self, frame_reference: Union[str, int, WebElement] = "frame"):
        """
        Switch to an iframe or frame.

        Args:
            frame_reference: Can be:
                - str: frame name or id (will wait for frame to be available)
                - int: frame index
                - WebElement: frame element

        Returns:
            The result of the switch operation
        """
        if isinstance(frame_reference, str):
            # Try to switch by name first, if that fails, try by ID
            # We use NAME as the locator because frame_to_be_available_and_switch_to_it
            # checks both name and id attributes
            return self._wait_on_selenium_condition(ec.frame_to_be_available_and_switch_to_it(frame_reference))
        elif isinstance(frame_reference, int):
            # Switch by index
            return self.driver.switch_to.frame(frame_reference)
        else:
            # Assume it's a WebElement
            return self.driver.switch_to.frame(frame_reference)

    def switch_to_default_content(self):
        """
        Switch back to the default content (main page context).

        This exits any iframe/frame context and returns to the top-level page.
        """
        self.driver.switch_to.default_content()

    def get_cookies(self) -> list[Cookie]:
        """
        Get all cookies for the current domain.

        Returns:
            List of cookie dictionaries with keys like 'name', 'value', 'domain', 'path', etc.
        """
        return _cookies_to_typed(self.driver.get_cookies())

    # Implementation of WaitMethodsMixin abstract methods for Selenium
    def _wait_on_condition_present(self, locator_tuple: tuple, message: str, **kwds) -> WebElement:
        """Wait for element to be present in DOM."""
        return self._wait_on_selenium_condition(ec.presence_of_element_located(locator_tuple), message, **kwds)

    def _wait_on_condition_visible(self, locator_tuple: tuple, message: str, **kwds) -> WebElement:
        """Wait for element to be visible."""
        return self._wait_on_selenium_condition(ec.visibility_of_element_located(locator_tuple), message, **kwds)

    def _wait_on_condition_clickable(self, locator_tuple: tuple, message: str, **kwds) -> WebElement:
        """Wait for element to be clickable."""
        return self._wait_on_selenium_condition(ec.element_to_be_clickable(locator_tuple), message, **kwds)

    def _wait_on_condition_invisible(self, locator_tuple: tuple, message: str, **kwds) -> WebElement:
        """Wait for element to be invisible or absent."""
        return self._wait_on_selenium_condition(ec.invisibility_of_element_located(locator_tuple), message, **kwds)

    def _wait_on_condition_absent(self, locator_tuple: tuple, message: str, **kwds) -> WebElement:
        """Wait for element to be completely absent from DOM."""
        return self._wait_on_selenium_condition(
            lambda driver: len(driver.find_elements(*locator_tuple)) == 0, message, **kwds
        )

    def _wait_on_condition_count(self, locator_tuple: tuple, n: int, message: str, **kwds) -> WebElement:
        """Wait for at least N elements."""
        return self._wait_on_selenium_condition(
            lambda driver: len(driver.find_elements(*locator_tuple)) >= n, message, **kwds
        )

    def _wait_on_custom(self, condition_func, message: str, **kwds) -> WebElement:
        """Wait on custom condition function."""
        return self._wait_on_selenium_condition(condition_func, message, **kwds)

    def click(self, selector_template: Target):
        element = self.driver.find_element(*selector_template.element_locator)
        element.click()

    def _wait_on_selenium_condition(self, condition, on_str: Optional[str] = None, **kwds):
        if on_str is None:
            on_str = str(condition)
        wait = self.wait(**kwds)
        return wait.until(condition, self._timeout_message(on_str))

    def action_chains(self):
        return ActionChains(self.driver)

    def drag_and_drop(self, source: WebElementProtocol, target: WebElementProtocol) -> None:
        """
        Drag and drop from source element to target element.

        Uses JavaScript-based drag and drop implementation for reliability.

        Args:
            source: The element to drag
            target: The element to drop onto
        """
        seletools_drag_and_drop(self.driver, source, target)

    def move_to_and_click(self, element: WebElementProtocol) -> None:
        """
        Move to an element and click it using ActionChains.

        This is useful when a simple click doesn't work due to element positioning.

        Args:
            element: The element to move to and click
        """
        self.action_chains().move_to_element(element).click().perform()

    def hover(self, element: WebElement) -> None:
        """
        Hover over an element (move mouse to element without clicking).

        Args:
            element: The element to hover over
        """
        self.action_chains().move_to_element(element).perform()

    def send_enter(self, element: Optional[WebElement] = None):
        self._send_key(Keys.ENTER, element)

    def send_escape(self, element: Optional[WebElement] = None):
        self._send_key(Keys.ESCAPE, element)

    def send_backspace(self, element: Optional[WebElement] = None):
        self._send_key(Keys.BACKSPACE, element)

    def aggressive_clear(self, element: WebElement) -> None:
        # for when a simple .clear() doesn't work
        self.driver.execute_script("arguments[0].value = '';", element)
        for _ in range(25):
            element.send_keys(Keys.BACKSPACE)

    def _send_key(self, key: str, element: Optional[WebElement] = None):
        if element is None:
            self.action_chains().send_keys(key)
        else:
            element.send_keys(key)

    @property
    @abc.abstractmethod
    def timeout_handler(self) -> TimeoutCallback:
        """Get timeout handler for application specific wait types."""
        ...

    def wait(self, timeout=UNSPECIFIED_TIMEOUT, wait_type: Optional[WaitTypeT] = None, **kwds):
        if timeout is UNSPECIFIED_TIMEOUT:
            timeout = self.timeout_handler(wait_type)
        return WebDriverWait(self.driver, timeout)

    def click_xpath(self, xpath: str):
        element = self.driver.find_element(By.XPATH, xpath)
        element.click()

    def click_label(self, text: str):
        element = self.driver.find_element(By.LINK_TEXT, text)
        element.click()

    def click_selector(self, selector: str):
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        element.click()

    def fill(self, form: WebElement, info: dict):
        for key, value in info.items():
            try:
                input_element = form.find_element(By.NAME, key)
            except NoSuchElementException:
                input_element = form.find_element(By.ID, key)
            input_element.send_keys(value)

    def click_submit(self, form: WebElement):
        submit_button = form.find_element(By.CSS_SELECTOR, "input[type='submit']")
        submit_button.click()

    def prepend_timeout_message(
        self, timeout_exception: SeleniumTimeoutException, message: str
    ) -> SeleniumTimeoutException:
        msg = message
        if timeout_msg := timeout_exception.msg:
            msg += f" {timeout_msg}"
        return SeleniumTimeoutException(
            msg=msg,
            screen=timeout_exception.screen,
            stacktrace=timeout_exception.stacktrace,
        )

    def accept_alert(self):
        """
        Return a context manager for accepting alerts.

        For Selenium, the alert must exist before it can be accepted,
        so we wait until the context exits to accept it.

        Usage:
            with driver.accept_alert():
                driver.click_selector("#button-that-shows-alert")
            # Alert is automatically accepted here
        """

        @contextmanager
        def _accept_alert_context():
            try:
                yield
            finally:
                # Accept the alert after the context block completes
                try:
                    alert = self.driver.switch_to.alert
                    alert.accept()
                finally:
                    self.driver.switch_to.default_content()

        return _accept_alert_context()

    def execute_script(self, script: str, *args):
        """
        Execute JavaScript in the current browser context.

        Args:
            script: JavaScript code to execute
            *args: Optional arguments to pass to the script (accessible as arguments[0], arguments[1], etc.)

        Returns:
            The return value of the script execution
        """
        return self.driver.execute_script(script, *args)

    def set_local_storage(self, key: str, value: Union[str, float]) -> None:
        """
        Set a value in the browser's localStorage.

        Args:
            key: The localStorage key
            value: The value to store (will be JSON-stringified if not a string)
        """
        self.execute_script(f"""window.localStorage.setItem("{key}", {value});""")

    def remove_local_storage(self, key: str) -> None:
        """
        Remove a key from the browser's localStorage.

        Args:
            key: The localStorage key to remove
        """
        self.execute_script(f"""window.localStorage.removeItem("{key}");""")

    def scroll_into_view(self, element: WebElement) -> None:
        """
        Scroll an element into view using JavaScript.

        Args:
            element: The element to scroll into view
        """
        self.execute_script("arguments[0].scrollIntoView(true);", element)

    def set_element_value(self, element: WebElement, value: str) -> None:
        """
        Set an element's value property directly using JavaScript.

        This is useful for contenteditable elements or when .clear() doesn't work.

        Args:
            element: The element to modify
            value: The value to set
        """
        self.execute_script(f"arguments[0].value = '{value}';", element)

    def execute_script_click(self, element: WebElement) -> None:
        """
        Click an element using JavaScript instead of Selenium's native click.

        This is useful when Selenium's click is intercepted or the element is not clickable.

        Args:
            element: The element to click
        """
        self.execute_script("arguments[0].click();", element)

    def find_element_by_link_text(self, text: str, element: Optional[WebElement] = None) -> WebElementProtocol:
        return _webelement_to_protocol(self._locator_aware(element).find_element(By.LINK_TEXT, text))

    def find_element_by_xpath(self, xpath: str, element: Optional[WebElement] = None) -> WebElementProtocol:
        return _webelement_to_protocol(self._locator_aware(element).find_element(By.XPATH, xpath))

    def find_element_by_id(self, id: str, element: Optional[WebElement] = None) -> WebElementProtocol:
        return _webelement_to_protocol(self._locator_aware(element).find_element(By.ID, id))

    def find_element_by_selector(self, selector: str, element: Optional[WebElement] = None) -> WebElementProtocol:
        return _webelement_to_protocol(self._locator_aware(element).find_element(By.CSS_SELECTOR, selector))

    def find_elements_by_selector(
        self, selector: str, element: Optional[WebElement] = None
    ) -> list[WebElementProtocol]:
        """
        Find multiple elements by CSS selector.

        Args:
            selector: CSS selector string
            element: Optional parent element to search within

        Returns:
            List of WebElementProtocol elements
        """
        elements = self._locator_aware(element).find_elements(By.CSS_SELECTOR, selector)
        return [_webelement_to_protocol(el) for el in elements]

    def get_input_value(self, element: WebElementProtocol) -> str:
        """
        Get the value of an input element.

        This provides a unified interface for getting input values across both
        Selenium and Playwright backends. For Selenium, this uses get_attribute("value").

        Args:
            element: The input element to get the value from

        Returns:
            The current value of the input element, or empty string if no value
        """
        value = element.get_attribute("value")
        return value if value is not None else ""

    def select_by_value(self, selector_template: HasElementLocator, value: str) -> None:
        """
        Select an option from a <select> element by its value attribute.

        Args:
            selector_template: Either a Target or a (locator_type, value) tuple for the select element
            value: The value attribute of the option to select
        """
        # Cast to WebElement - we know this is actually a WebElement in the Selenium backend
        select_element = self.find_element(selector_template)
        assert isinstance(select_element, WebElement)
        select = Select(select_element)
        select.select_by_value(value)

    def axe_eval(self, context: Optional[str] = None, write_to: Optional[str] = None) -> AxeResults:
        if self.axe_skip:
            return NullAxeResults()

        content = get_axe_script(self.axe_script_url)
        self.driver.execute_script(content)
        axe = Axe(self.driver)
        results = axe.run(context=context)
        if write_to is not None:
            axe.write_results(results, write_to)
        return RealAxeResults(results)

    def save_screenshot(self, path: str) -> None:
        """
        Save a screenshot to the specified path.

        Args:
            path: File path where the screenshot should be saved
        """
        self.driver.save_screenshot(path)

    def get_screenshot_as_png(self) -> bytes:
        """
        Capture a screenshot and return it as PNG bytes.

        Returns:
            PNG image data as bytes
        """
        return self.driver.get_screenshot_as_png()

    def quit(self) -> None:
        """
        Clean up and close the driver/browser.

        This closes all windows/tabs and releases all system resources.
        The driver cannot be used after calling this method.
        """
        self.driver.quit()

    def _locator_aware(self, element: Optional[WebElement] = None) -> HasFindElement:
        if element is None:
            return self.driver
        else:
            return element

    def double_click(self, element: WebElement) -> None:
        """
        Double-click an element using ActionChains.

        Args:
            element: The element to double-click
        """
        action_chains = self.action_chains()
        action_chains.move_to_element(element).double_click().perform()

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


def exception_indicates_click_intercepted(exception):
    return "click intercepted" in str(exception)


def exception_indicates_not_clickable(exception):
    selenium_not_clickable = "not clickable" in str(exception)
    playwright_not_enabled = "element is not enabled" in str(exception)
    return selenium_not_clickable or playwright_not_enabled


def exception_indicates_stale_element(exception):
    return "stale" in str(exception)


__all__ = (
    "exception_indicates_click_intercepted",
    "exception_indicates_not_clickable",
    "exception_indicates_stale_element",
    "HasDriver",
    "SeleniumTimeoutException",
    "TimeoutMessageMixin",
)
