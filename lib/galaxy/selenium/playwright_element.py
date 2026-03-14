"""Playwright element wrapper that implements WebElementProtocol.

This module provides PlaywrightElement, a wrapper around Playwright's ElementHandle
that implements the WebElementProtocol interface, making it compatible with code
written for Selenium's WebElement.
"""

from typing import (
    Optional,
    TYPE_CHECKING,
)

from playwright.sync_api import (
    ElementHandle,
    JSHandle,
)
from selenium.webdriver.common.keys import Keys

# Map Selenium Key unicode constants to Playwright key names
_SELENIUM_KEY_TO_PLAYWRIGHT = {
    Keys.CONTROL: "Control",
    Keys.COMMAND: "Meta",
    Keys.META: "Meta",
    Keys.SHIFT: "Shift",
    Keys.ALT: "Alt",
    Keys.ENTER: "Enter",
    Keys.RETURN: "Enter",
    Keys.ESCAPE: "Escape",
    Keys.BACKSPACE: "Backspace",
    Keys.DELETE: "Delete",
    Keys.TAB: "Tab",
    Keys.SPACE: " ",
    Keys.ARROW_DOWN: "ArrowDown",
    Keys.ARROW_UP: "ArrowUp",
    Keys.ARROW_LEFT: "ArrowLeft",
    Keys.ARROW_RIGHT: "ArrowRight",
    Keys.HOME: "Home",
    Keys.END: "End",
    Keys.PAGE_UP: "PageUp",
    Keys.PAGE_DOWN: "PageDown",
}

_SELENIUM_MODIFIERS = {Keys.CONTROL, Keys.COMMAND, Keys.META, Keys.SHIFT, Keys.ALT}

if TYPE_CHECKING:
    from .has_playwright_driver import HasPlaywrightDriver
    from .web_element_protocol import WebElementProtocol


class PlaywrightShadowRoot:
    """Wrapper around a shadow root JSHandle that provides find_element support."""

    def __init__(self, shadow_root_handle: JSHandle, driver: "HasPlaywrightDriver"):
        self._shadow_root = shadow_root_handle
        self._driver = driver

    def find_element(self, by: str = "id", value: Optional[str] = None) -> "WebElementProtocol":
        if value is None:
            raise ValueError("value parameter is required")
        selector = self._driver._selenium_locator_to_playwright_selector(by, value)
        result_handle = self._shadow_root.evaluate_handle(f"root => root.querySelector('{selector}')")
        element_handle = result_handle.as_element()
        if element_handle:
            return PlaywrightElement(element_handle, self._driver)
        raise Exception(f"No element found in shadow root with {by}='{value}'")


class PlaywrightElement:
    """
    Wrapper around Playwright ElementHandle that implements WebElementProtocol.

    This adapter makes Playwright's ElementHandle compatible with Selenium's
    WebElement API, allowing the same code to work with both backends.
    """

    def __init__(self, element_handle: ElementHandle, driver: "HasPlaywrightDriver"):
        self._element = element_handle
        self._driver = driver

    @property
    def text(self) -> str:
        """
        Get the visible text content of the element.

        Uses Playwright's inner_text() to match Selenium's .text behavior
        which returns rendered text with normalized whitespace.
        """
        content = self._element.inner_text()
        return content.strip() if content is not None else ""

    def click(self) -> None:
        """Click the element."""
        self._element.click()

    def send_keys(self, *value: str) -> None:
        """
        Send keys to the element (type text).

        Translates Selenium Keys constants to Playwright keyboard actions.
        Modifier keys (Control, Command, etc.) combine with the next key
        as a keyboard shortcut (e.g. Keys.CONTROL, "a" -> "Control+a").
        """
        self._element.focus()
        # Flatten all args into a single character stream
        all_chars = "".join(str(v) for v in value)
        has_special = any(c in _SELENIUM_KEY_TO_PLAYWRIGHT for c in all_chars)
        if not has_special:
            self._element.evaluate(
                "el => { try { if (el.setSelectionRange) el.setSelectionRange(el.value.length, el.value.length) } catch(e) {} }"
            )
            self._element.type(all_chars)
        else:
            modifiers: list[str] = []
            for char in all_chars:
                pw_key = _SELENIUM_KEY_TO_PLAYWRIGHT.get(char)
                if pw_key and char in _SELENIUM_MODIFIERS:
                    modifiers.append(pw_key)
                elif pw_key:
                    combo = "+".join(modifiers + [pw_key])
                    self._element.press(combo)
                    modifiers.clear()
                else:
                    if modifiers:
                        combo = "+".join(modifiers + [char])
                        self._element.press(combo)
                        modifiers.clear()
                    else:
                        self._element.type(char)

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

    def is_selected(self) -> bool:
        """
        Check if element is selected (for checkboxes, radio buttons, options).

        Maps to Playwright's is_checked() method.
        """
        return self._element.is_checked()

    def submit(self) -> None:
        """
        Submit a form element.

        Uses JavaScript to trigger form submission.
        """
        self._element.evaluate("(el) => el.form ? el.form.submit() : el.submit()")

    @property
    def shadow_root(self) -> PlaywrightShadowRoot:
        """Access the shadow root of this element, matching Selenium's WebElement.shadow_root."""
        handle = self._element.evaluate_handle("el => el.shadowRoot")
        return PlaywrightShadowRoot(handle, self._driver)

    def find_element(self, by: str = "id", value: Optional[str] = None) -> "WebElementProtocol":
        """Find a child element within this element."""
        if value is None:
            raise ValueError("value parameter is required")
        selector = self._driver._selenium_locator_to_playwright_selector(by, value)
        found_element = self._element.query_selector(selector)
        if found_element:
            return PlaywrightElement(found_element, self._driver)
        raise Exception(f"No element found with {by}='{value}'")

    def find_elements(self, by: str = "id", value: Optional[str] = None) -> list["WebElementProtocol"]:
        """Find all child elements matching the locator within this element."""
        if value is None:
            raise ValueError("value parameter is required")
        selector = self._driver._selenium_locator_to_playwright_selector(by, value)
        found_elements = self._element.query_selector_all(selector)
        return [PlaywrightElement(elem, self._driver) for elem in found_elements]

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
