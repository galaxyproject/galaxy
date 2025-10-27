"""Playwright element wrapper that implements WebElementProtocol.

This module provides PlaywrightElement, a wrapper around Playwright's ElementHandle
that implements the WebElementProtocol interface, making it compatible with code
written for Selenium's WebElement.
"""

from typing import (
    Optional,
    TYPE_CHECKING,
)

from playwright.sync_api import ElementHandle

if TYPE_CHECKING:
    from .web_element_protocol import WebElementProtocol


class PlaywrightElement:
    """
    Wrapper around Playwright ElementHandle that implements WebElementProtocol.

    This adapter makes Playwright's ElementHandle compatible with Selenium's
    WebElement API, allowing the same code to work with both backends.
    """

    def __init__(self, element_handle: ElementHandle, driver):
        """
        Initialize PlaywrightElement wrapper.

        Args:
            element_handle: The Playwright ElementHandle to wrap
            driver: The HasPlaywrightDriver instance (for find_element operations)
        """
        self._element = element_handle
        self._driver = driver

    @property
    def text(self) -> str:
        """
        Get the visible text content of the element.

        Maps to Playwright's text_content() method.
        """
        content = self._element.text_content()
        return content.strip() if content is not None else ""

    def click(self) -> None:
        """Click the element."""
        self._element.click()

    def send_keys(self, *value: str) -> None:
        """
        Send keys to the element (type text).

        Playwright requires elements to be focused before typing, so we click first.

        Args:
            *value: Text strings to type (will be concatenated)
        """
        text = "".join(str(v) for v in value)
        # Playwright requires focus before typing
        self._element.click()
        self._element.type(text)

    def clear(self) -> None:
        """
        Clear the text of an input or textarea element.

        Uses Playwright's fill() method with empty string.
        """
        self._element.fill("")

    def get_attribute(self, name: str) -> Optional[str]:
        """
        Get the value of an element attribute.

        For input elements, "value" is special-cased to use input_value()
        to match Selenium behavior.

        Args:
            name: The attribute name

        Returns:
            The attribute value, or None if not found
        """
        # Special case: for input elements, "value" needs to use input_value()
        if name == "value":
            try:
                # Try to get input value (works for input/textarea/select)
                return self._element.input_value()
            except Exception:
                # Fall back to regular attribute if not an input element
                pass
        return self._element.get_attribute(name)

    def is_displayed(self) -> bool:
        """
        Check if the element is visible on the page.

        Maps to Playwright's is_visible() method.
        """
        return self._element.is_visible()

    def is_enabled(self) -> bool:
        """
        Check if the element is enabled (not disabled).

        Maps to Playwright's is_enabled() method.
        """
        return self._element.is_enabled()

    def submit(self) -> None:
        """
        Submit a form element.

        Uses JavaScript to trigger form submission.
        """
        self._element.evaluate("(el) => el.form ? el.form.submit() : el.submit()")

    def find_element(self, by: str = "id", value: Optional[str] = None) -> "WebElementProtocol":
        """
        Find a child element within this element.

        Delegates to the driver's element finding logic.

        Args:
            by: The locator strategy (e.g., "id", "css selector")
            value: The locator value

        Returns:
            A PlaywrightElement wrapping the found ElementHandle
        """
        # Convert the locator to Playwright selector
        from .has_playwright_driver import HasPlaywrightDriver

        if isinstance(self._driver, HasPlaywrightDriver):
            if value is None:
                raise ValueError("value parameter is required")
            selector = self._driver._selenium_locator_to_playwright_selector(by, value)
            # Use ElementHandle's query_selector to find within this element
            found_element = self._element.query_selector(selector)
            if found_element:
                return PlaywrightElement(found_element, self._driver)
            raise Exception(f"No element found with {by}='{value}'")

        raise NotImplementedError("find_element within element not yet fully implemented")

    def find_elements(self, by: str = "id", value: Optional[str] = None) -> list["WebElementProtocol"]:
        """
        Find all child elements matching the locator within this element.

        Delegates to the driver's element finding logic.

        Args:
            by: The locator strategy (e.g., "css selector", "xpath")
            value: The locator value

        Returns:
            List of PlaywrightElement instances
        """
        from .has_playwright_driver import HasPlaywrightDriver

        if isinstance(self._driver, HasPlaywrightDriver):
            if value is None:
                raise ValueError("value parameter is required")
            selector = self._driver._selenium_locator_to_playwright_selector(by, value)
            found_elements = self._element.query_selector_all(selector)
            return [PlaywrightElement(elem, self._driver) for elem in found_elements]

        raise NotImplementedError("find_elements within element not yet fully implemented")

    def content_frame(self):
        """
        Get the frame associated with this iframe/frame element.

        Returns:
            The Frame associated with this element, or None if not a frame element
        """
        return self._element.content_frame()

    def value_of_css_property(self, property_name: str) -> str:
        """
        Get the value of a CSS property for this element.

        Uses JavaScript's window.getComputedStyle() to get the computed value
        of the specified CSS property.

        Args:
            property_name: The CSS property name (e.g., "color", "display", "font-size")

        Returns:
            The computed CSS property value as a string
        """
        value = self._element.evaluate(
            "(element, propName) => window.getComputedStyle(element).getPropertyValue(propName)", property_name
        )
        return str(value) if value is not None else ""

    # Expose the underlying ElementHandle for special cases
    @property
    def element_handle(self) -> ElementHandle:
        """Get the underlying Playwright ElementHandle (for advanced use cases)."""
        return self._element


__all__ = ("PlaywrightElement",)
