"""Mixin providing common wait methods that work across Selenium and Playwright."""

from typing import Any

from galaxy.navigation.components import Target


class WaitMethodsMixin:
    """
    Mixin providing high-level wait methods.

    This mixin abstracts wait operations to work with both Selenium and Playwright
    by delegating to implementation-specific condition methods.
    """

    def wait_for_xpath(self, xpath: str, **kwds) -> Any:
        """Wait for element to be present by XPath."""
        return self._wait_on_condition_present(("xpath", xpath), f"XPATH selector [{xpath}] to become present", **kwds)

    def wait_for_xpath_visible(self, xpath: str, **kwds) -> Any:
        """Wait for element to be visible by XPath."""
        return self._wait_on_condition_visible(("xpath", xpath), f"XPATH selector [{xpath}] to become visible", **kwds)

    def wait_for_selector(self, selector: str, **kwds) -> Any:
        """Wait for element to be present by CSS selector."""
        return self._wait_on_condition_present(
            ("css selector", selector), f"CSS selector [{selector}] to become present", **kwds
        )

    def wait_for_present(self, selector_template: Target, **kwds) -> Any:
        """Wait for element to be present using Target."""
        return self._wait_on_condition_present(
            selector_template.element_locator, f"{selector_template.description} to become present", **kwds
        )

    def wait_for_visible(self, selector_template: Target, **kwds) -> Any:
        """Wait for element to be visible using Target."""
        return self._wait_on_condition_visible(
            selector_template.element_locator, f"{selector_template.description} to become visible", **kwds
        )

    def wait_for_selector_visible(self, selector: str, **kwds) -> Any:
        """Wait for element to be visible by CSS selector."""
        return self._wait_on_condition_visible(
            ("css selector", selector), f"CSS selector [{selector}] to become visible", **kwds
        )

    def wait_for_selector_clickable(self, selector: str, **kwds) -> Any:
        """Wait for element to be clickable by CSS selector."""
        return self._wait_on_condition_clickable(
            ("css selector", selector), f"CSS selector [{selector}] to become clickable", **kwds
        )

    def wait_for_clickable(self, selector_template: Target, **kwds) -> Any:
        """Wait for element to be clickable using Target."""
        return self._wait_on_condition_clickable(
            selector_template.element_locator, f"{selector_template.description} to become clickable", **kwds
        )

    def wait_for_selector_absent_or_hidden(self, selector: str, **kwds) -> Any:
        """Wait for element to be absent or hidden by CSS selector."""
        return self._wait_on_condition_invisible(
            ("css selector", selector), f"CSS selector [{selector}] to become absent or hidden", **kwds
        )

    def wait_for_selector_absent(self, selector: str, **kwds) -> Any:
        """Wait for element to be absent by CSS selector."""
        return self._wait_on_condition_absent(
            ("css selector", selector), f"CSS selector [{selector}] to become absent", **kwds
        )

    def wait_for_element_count_of_at_least(self, selector_template: Target, n: int, **kwds) -> Any:
        """Wait for at least N elements matching Target."""
        return self._wait_on_condition_count(
            selector_template.element_locator,
            n,
            f"{selector_template.description} to have at least {n} elements",
            **kwds,
        )

    def wait_for_absent(self, selector_template: Target, **kwds) -> Any:
        """Wait for element to be absent using Target."""
        return self._wait_on_condition_absent(
            selector_template.element_locator, f"{selector_template.description} to become absent", **kwds
        )

    def wait_for_absent_or_hidden(self, selector_template: Target, **kwds) -> Any:
        """Wait for element to be absent or hidden using Target."""
        return self._wait_on_condition_invisible(
            selector_template.element_locator, f"{selector_template.description} to become absent or hidden", **kwds
        )

    def wait_for_id(self, id: str, **kwds) -> Any:
        """Wait for element to be present by ID."""
        return self._wait_on_condition_present(("id", id), f"presence of DOM ID [{id}]", **kwds)

    def wait_for_and_click(self, selector_template: Target, **kwds) -> Any:
        """
        Wait for element to be clickable and then click it.

        Args:
            selector_template: Target selector for the element
            **kwds: Additional keyword arguments for wait (e.g., timeout)

        Returns:
            The clicked element
        """
        element = self.wait_for_clickable(selector_template, **kwds)
        element.click()
        return element

    def wait_for_and_double_click(self, selector_template: Target, **kwds) -> Any:
        """
        Wait for element to be clickable and then double-click it.

        Requires implementing class to provide double_click(element) method.

        Args:
            selector_template: Target selector for the element
            **kwds: Additional keyword arguments for wait (e.g., timeout)

        Returns:
            The double-clicked element
        """
        element = self.wait_for_clickable(selector_template, **kwds)
        self.double_click(element)
        return element

    # Abstract methods that must be implemented by subclasses
    def _wait_on_condition_present(self, locator_tuple: tuple, message: str, **kwds) -> Any:
        """Wait for element to be present in DOM."""
        raise NotImplementedError()

    def _wait_on_condition_visible(self, locator_tuple: tuple, message: str, **kwds) -> Any:
        """Wait for element to be visible."""
        raise NotImplementedError()

    def _wait_on_condition_clickable(self, locator_tuple: tuple, message: str, **kwds) -> Any:
        """Wait for element to be clickable."""
        raise NotImplementedError()

    def _wait_on_condition_invisible(self, locator_tuple: tuple, message: str, **kwds) -> Any:
        """Wait for element to be invisible or absent."""
        raise NotImplementedError()

    def _wait_on_condition_absent(self, locator_tuple: tuple, message: str, **kwds) -> Any:
        """Wait for element to be completely absent from DOM."""
        raise NotImplementedError()

    def _wait_on_condition_count(self, locator_tuple: tuple, n: int, message: str, **kwds) -> Any:
        """Wait for at least N elements."""
        raise NotImplementedError()

    def _wait_on_custom(self, condition_func, message: str, **kwds) -> Any:
        """Wait on custom condition function."""
        raise NotImplementedError()

    def double_click(self, element) -> None:
        """Double-click an element (must be implemented by subclass)."""
        raise NotImplementedError()


__all__ = ("WaitMethodsMixin",)
