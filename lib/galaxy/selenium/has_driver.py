"""A mixin to extend a class that has self.driver with higher-level constructs.

This should be mixed into classes with a self.driver and self.default_timeout
attribute.
"""

import abc
import threading
from typing import (
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
from selenium.webdriver.support.wait import WebDriverWait
from seletools.actions import drag_and_drop as seletools_drag_and_drop

from galaxy.navigation.components import Target
from galaxy.util import requests
from .axe_results import (
    AxeResults,
    NullAxeResults,
    RealAxeResults,
)
from .wait_methods_mixin import WaitMethodsMixin

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


class HasDriver(WaitMethodsMixin):
    by: type[By] = By
    keys: type[Keys] = Keys
    driver: WebDriver
    axe_script_url: str = DEFAULT_AXE_SCRIPT_URL
    axe_skip: bool = False

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

    def find_elements(self, selector_template: Target) -> list[WebElement]:
        return self.driver.find_elements(*selector_template.element_locator)

    def find_element(self, selector_template: Target) -> WebElementProtocol:
        """Find first element matching Target (no waiting)."""
        return _webelement_to_protocol(self.driver.find_element(*selector_template.element_locator))

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
            return self._wait_on(ec.frame_to_be_available_and_switch_to_it((By.NAME, frame_reference)))
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

    def get_cookies(self) -> list[dict]:
        """
        Get all cookies for the current domain.

        Returns:
            List of cookie dictionaries with keys like 'name', 'value', 'domain', 'path', etc.
        """
        return self.driver.get_cookies()

    # Implementation of WaitMethodsMixin abstract methods for Selenium
    def _wait_on_condition_present(self, locator_tuple: tuple, message: str, **kwds) -> WebElement:
        """Wait for element to be present in DOM."""
        return self._wait_on(ec.presence_of_element_located(locator_tuple), message, **kwds)

    def _wait_on_condition_visible(self, locator_tuple: tuple, message: str, **kwds) -> WebElement:
        """Wait for element to be visible."""
        return self._wait_on(ec.visibility_of_element_located(locator_tuple), message, **kwds)

    def _wait_on_condition_clickable(self, locator_tuple: tuple, message: str, **kwds) -> WebElement:
        """Wait for element to be clickable."""
        return self._wait_on(ec.element_to_be_clickable(locator_tuple), message, **kwds)

    def _wait_on_condition_invisible(self, locator_tuple: tuple, message: str, **kwds) -> WebElement:
        """Wait for element to be invisible or absent."""
        return self._wait_on(ec.invisibility_of_element_located(locator_tuple), message, **kwds)

    def _wait_on_condition_absent(self, locator_tuple: tuple, message: str, **kwds) -> WebElement:
        """Wait for element to be completely absent from DOM."""
        return self._wait_on(lambda driver: len(driver.find_elements(*locator_tuple)) == 0, message, **kwds)

    def _wait_on_condition_count(self, locator_tuple: tuple, n: int, message: str, **kwds) -> WebElement:
        """Wait for at least N elements."""
        return self._wait_on(lambda driver: len(driver.find_elements(*locator_tuple)) >= n, message, **kwds)

    def _wait_on_custom(self, condition_func, message: str, **kwds) -> WebElement:
        """Wait on custom condition function."""
        return self._wait_on(condition_func, message, **kwds)

    def click(self, selector_template: Target):
        element = self.driver.find_element(*selector_template.element_locator)
        element.click()

    def _timeout_message(self, on_str: str) -> str:
        return f"Timeout waiting on {on_str}."

    def _wait_on(self, condition, on_str: Optional[str] = None, **kwds):
        if on_str is None:
            on_str = str(condition)
        wait = self.wait(**kwds)
        return wait.until(condition, self._timeout_message(on_str))

    def action_chains(self):
        return ActionChains(self.driver)

    def drag_and_drop(self, source: WebElement, target: WebElement) -> None:
        """
        Drag and drop from source element to target element.

        Uses JavaScript-based drag and drop implementation for reliability.

        Args:
            source: The element to drag
            target: The element to drop onto
        """
        seletools_drag_and_drop(self.driver, source, target)

    def move_to_and_click(self, element: WebElement) -> None:
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

    @abc.abstractmethod
    def timeout_for(self, **kwds) -> float: ...

    def wait(self, timeout=UNSPECIFIED_TIMEOUT, **kwds):
        if timeout is UNSPECIFIED_TIMEOUT:
            timeout = self.timeout_for(**kwds)
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
        try:
            alert = self.driver.switch_to.alert
            alert.accept()
        finally:
            self.driver.switch_to.default_content()

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

    def set_local_storage(self, key: str, value: str) -> None:
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

    def find_element_by_link_text(self, text: str, element: Optional[WebElement] = None) -> WebElement:
        return self._locator_aware(element).find_element(By.LINK_TEXT, text)

    def find_element_by_xpath(self, xpath: str, element: Optional[WebElement] = None) -> WebElement:
        return self._locator_aware(element).find_element(By.XPATH, xpath)

    def find_element_by_id(self, id: str, element: Optional[WebElement] = None) -> WebElement:
        return self._locator_aware(element).find_element(By.ID, id)

    def find_element_by_selector(self, selector: str, element: Optional[WebElement] = None) -> WebElement:
        return self._locator_aware(element).find_element(By.CSS_SELECTOR, selector)

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
    return "not clickable" in str(exception)


def exception_indicates_stale_element(exception):
    return "stale" in str(exception)


__all__ = (
    "exception_indicates_click_intercepted",
    "exception_indicates_not_clickable",
    "exception_indicates_stale_element",
    "HasDriver",
    "SeleniumTimeoutException",
)
