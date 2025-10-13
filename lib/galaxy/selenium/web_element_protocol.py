"""Protocol for unified WebElement interface.

This module defines a Protocol that abstracts the common WebElement API
used in navigates_galaxy.py and tests. Both Selenium WebElement and our
PlaywrightElement wrapper implement this protocol.
"""

from typing import (
    Optional,
    Protocol,
    runtime_checkable,
)


@runtime_checkable
class WebElementProtocol(Protocol):
    """
    Protocol defining the WebElement API used in Galaxy Selenium tests.

    This protocol captures the subset of WebElement methods that are actually
    used in navigates_galaxy.py and test code. Both Selenium's WebElement and
    our PlaywrightElement wrapper implement this protocol.

    Methods used (from navigates_galaxy.py usage analysis):
    - .text (31 uses) - Get visible text content
    - .click() (39 uses) - Click the element
    - .send_keys() (28 uses) - Type text into element
    - .clear() (21 uses) - Clear input field
    - .get_attribute() (7 uses) - Get element attribute
    - .is_displayed() (4 uses) - Check if element is visible
    - .submit() (8 uses) - Submit form
    - .find_element() (33 uses) - Find child element
    - .find_elements() (25 uses) - Find child elements
    """

    @property
    def text(self) -> str:
        """Get the visible text content of the element."""
        ...

    def click(self) -> None:
        """Click the element."""
        ...

    def send_keys(self, *value: str) -> None:
        """Send keys to the element (type text)."""
        ...

    def clear(self) -> None:
        """Clear the text of an input or textarea element."""
        ...

    def get_attribute(self, name: str) -> Optional[str]:
        """Get the value of an element attribute."""
        ...

    def is_displayed(self) -> bool:
        """Check if the element is visible on the page."""
        ...

    def is_enabled(self) -> bool:
        """Check if the element is enabled (not disabled)."""
        ...

    def submit(self) -> None:
        """Submit a form element."""
        ...

    def find_element(self, by: str = "id", value: Optional[str] = None) -> "WebElementProtocol":
        """Find a child element within this element."""
        ...

    def find_elements(self, by: str = "id", value: Optional[str] = None) -> list["WebElementProtocol"]:
        """Find all child elements matching the locator within this element."""
        ...


__all__ = ("WebElementProtocol",)
