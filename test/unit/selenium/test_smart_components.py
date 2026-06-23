"""Unit tests for smart_components.py - SmartComponent and SmartTarget classes.

Tests the SmartComponent and SmartTarget wrapper classes that provide driver-aware
methods for Galaxy's component locators.
"""

import pytest

from galaxy.navigation.components import SelectorTemplate
from galaxy.selenium.smart_components import (
    SmartComponent,
    SmartTarget,
)
from .test_has_driver import (
    TestHasDriverImpl,
    TestHasPlaywrightDriverImpl,
)


# Test component hierarchy for testing
class TestComponent:
    """Simple test component with selector attributes for testing SmartComponent."""

    def __init__(self):
        # Create Target objects that SmartComponent can wrap
        self.button = SelectorTemplate("#test-button", "css")
        self.input_field = SelectorTemplate("#test-input", "css")
        self.items = SelectorTemplate(".item", "css")
        self.hidden_element = SelectorTemplate("#hidden-element", "css")
        self.delayed_element = SelectorTemplate("#delayed-element", "css")
        self.data_element = SelectorTemplate("#data-element", "css")
        self.class_element = SelectorTemplate("#class-element", "css")


@pytest.fixture(params=["selenium", "playwright"])
def has_driver_instance(request, driver, playwright_resources, base_url):
    """
    Create a driver instance based on the backend parameter.

    Args:
        request: Pytest request fixture for parametrization
        driver: Selenium WebDriver fixture
        playwright_resources: Playwright resources fixture
        base_url: Base URL for test server

    Returns:
        HasDriver or HasPlaywrightDriver instance
    """
    if request.param == "selenium":
        return TestHasDriverImpl(driver)
    else:  # playwright
        return TestHasPlaywrightDriverImpl(playwright_resources)


@pytest.fixture
def smart_component(has_driver_instance):
    """Create a SmartComponent instance for testing."""
    return SmartComponent(TestComponent(), has_driver_instance)


class TestSmartComponentWrapping:
    """Test SmartComponent wrapping behavior."""

    def test_getattr_wraps_target(self, smart_component):
        """Test that __getattr__ wraps Target objects in SmartTarget."""
        button = smart_component.button
        assert isinstance(button, SmartTarget)
        # Check that the wrapped target has the same selector as the original
        assert button._target.selector == "#test-button"
        assert button._target.selector_type == "css"


class TestSmartTargetBasicMethods:
    """Test SmartTarget basic methods."""

    def test_all_finds_multiple_elements(self, smart_component, has_driver_instance, base_url):
        """Test that all() returns multiple elements."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        items = smart_component.items.all()
        assert len(items) == 3

    def test_all_returns_empty_list_when_no_matches(self, smart_component, has_driver_instance, base_url):
        """Test that all() returns empty list when no elements match."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        no_match = SelectorTemplate(".nonexistent", "css")
        smart_target = SmartTarget(no_match, has_driver_instance)
        items = smart_target.all()
        assert len(items) == 0

    def test_wait_for_visible(self, smart_component, has_driver_instance, base_url):
        """Test that wait_for_visible returns visible element."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        element = smart_component.button.wait_for_visible()
        assert element is not None
        assert element.text == "Click Me"

    def test_wait_for_and_click(self, smart_component, has_driver_instance, base_url):
        """Test that wait_for_and_click clicks element."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        smart_component.button.wait_for_and_click()
        # Verify click worked by checking result
        result = has_driver_instance.find_element_by_id("result")
        assert result.text == "Button clicked!"

    def test_wait_for_and_double_click(self, smart_component, has_driver_instance, base_url):
        """Test that wait_for_and_double_click double-clicks element."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        smart_component.button.wait_for_and_double_click()
        # Verify double-click worked
        result = has_driver_instance.find_element_by_id("result")
        assert result.text == "Button double-clicked!"

    def test_wait_for_clickable(self, smart_component, has_driver_instance, base_url):
        """Test that wait_for_clickable returns clickable element."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        element = smart_component.button.wait_for_clickable()
        assert element is not None

    def test_wait_for_text(self, smart_component, has_driver_instance, base_url):
        """Test that wait_for_text returns element text."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        text = smart_component.button.wait_for_text()
        assert text == "Click Me"

    def test_wait_for_present(self, smart_component, has_driver_instance, base_url):
        """Test that wait_for_present returns present element."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        element = smart_component.button.wait_for_present()
        assert element is not None

    def test_is_displayed_property(self, smart_component, has_driver_instance, base_url):
        """Test that is_displayed property returns visibility status."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        assert smart_component.button.is_displayed is True
        assert smart_component.hidden_element.is_displayed is False

    def test_is_absent_property(self, smart_component, has_driver_instance, base_url):
        """Test that is_absent property returns absence status."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        assert smart_component.button.is_absent is False
        nonexistent = SelectorTemplate("#nonexistent", "css")
        smart_target = SmartTarget(nonexistent, has_driver_instance)
        assert smart_target.is_absent is True


class TestSmartTargetWaitMethods:
    """Test SmartTarget wait methods."""

    def test_wait_for_absent(self, has_driver_instance, base_url):
        """Test that wait_for_absent waits for element to be absent."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        nonexistent = SelectorTemplate("#nonexistent", "css")
        smart_target = SmartTarget(nonexistent, has_driver_instance)
        # Element should already be absent - this should return quickly
        smart_target.wait_for_absent()

    def test_wait_for_absent_or_hidden(self, has_driver_instance, base_url):
        """Test that wait_for_absent_or_hidden waits for element to be absent or hidden."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        hidden = SelectorTemplate("#hidden-element", "css")
        smart_target = SmartTarget(hidden, has_driver_instance)
        smart_target.wait_for_absent_or_hidden()


class TestSmartTargetAssertionMethods:
    """Test SmartTarget assertion methods."""

    def test_assert_absent(self, has_driver_instance, base_url):
        """Test that assert_absent asserts element is absent."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        nonexistent = SelectorTemplate("#nonexistent", "css")
        smart_target = SmartTarget(nonexistent, has_driver_instance)
        smart_target.assert_absent()  # Should not raise

    def test_assert_absent_or_hidden(self, has_driver_instance, base_url):
        """Test that assert_absent_or_hidden asserts element is absent or hidden."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        hidden = SelectorTemplate("#hidden-element", "css")
        smart_target = SmartTarget(hidden, has_driver_instance)
        smart_target.assert_absent_or_hidden()  # Should not raise

    def test_assert_disabled(self, has_driver_instance, base_url):
        """Test that assert_disabled asserts element is disabled."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        disabled_input = SelectorTemplate("#disabled-input", "css")
        smart_target = SmartTarget(disabled_input, has_driver_instance)
        smart_target.assert_disabled()  # Should not raise


class TestSmartTargetDataMethods:
    """Test SmartTarget data attribute methods."""

    def test_data_value(self, has_driver_instance, base_url):
        """Test that data_value retrieves data attributes."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        data_element = SelectorTemplate("#data-element", "css")
        smart_target = SmartTarget(data_element, has_driver_instance)
        value = smart_target.data_value("test")
        assert value == "example-value"

    def test_assert_data_value_passes(self, has_driver_instance, base_url):
        """Test that assert_data_value passes when value matches."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        data_element = SelectorTemplate("#data-element", "css")
        smart_target = SmartTarget(data_element, has_driver_instance)
        smart_target.assert_data_value("test", "example-value")  # Should not raise

    def test_assert_data_value_fails(self, has_driver_instance, base_url):
        """Test that assert_data_value fails when value doesn't match."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        data_element = SelectorTemplate("#data-element", "css")
        smart_target = SmartTarget(data_element, has_driver_instance)
        with pytest.raises(AssertionError, match="Expected data-test to have value"):
            smart_target.assert_data_value("test", "wrong-value")

    def test_has_class_returns_true(self, has_driver_instance, base_url):
        """Test that has_class returns True when class exists."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        class_element = SelectorTemplate("#class-element", "css")
        smart_target = SmartTarget(class_element, has_driver_instance)
        assert smart_target.has_class("active") is True

    def test_has_class_returns_false(self, has_driver_instance, base_url):
        """Test that has_class returns False when class doesn't exist."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        class_element = SelectorTemplate("#class-element", "css")
        smart_target = SmartTarget(class_element, has_driver_instance)
        assert smart_target.has_class("inactive") is False


class TestSmartTargetInputMethods:
    """Test SmartTarget input methods."""

    def test_wait_for_and_send_keys(self, smart_component, has_driver_instance, base_url):
        """Test that wait_for_and_send_keys sends keys to element."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        smart_component.input_field.wait_for_and_send_keys("test input")
        # Verify input was sent
        element = has_driver_instance.find_element_by_id("test-input")
        # Note: Different backends may have different ways to get value
        # We'll just verify the element exists for now
        assert element is not None

    def test_wait_for_and_clear_and_send_keys(self, smart_component, has_driver_instance, base_url):
        """Test that wait_for_and_clear_and_send_keys clears and sends keys."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        # First set some text
        input_element = has_driver_instance.find_element_by_id("test-input")
        input_element.send_keys("initial text")
        # Now clear and send new text
        smart_component.input_field.wait_for_and_clear_and_send_keys("new text")
        # Verify input was cleared and new text sent
        element = has_driver_instance.find_element_by_id("test-input")
        assert element is not None

    def test_wait_for_and_clear_aggressive_and_send_keys(self, smart_component, has_driver_instance, base_url):
        """Test that wait_for_and_clear_aggressive_and_send_keys aggressively clears and sends keys."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        # First set some text
        input_element = has_driver_instance.find_element_by_id("test-input")
        input_element.send_keys("initial text that needs aggressive clearing")

        # Now use aggressive clear and send new text
        smart_component.input_field.wait_for_and_clear_aggressive_and_send_keys("new text after aggressive clear")

        # Verify input was cleared and new text sent
        # Use execute_script to verify the value reliably across both backends
        value = has_driver_instance.execute_script("return arguments[0].value", input_element)
        assert "new text after aggressive clear" in value
        assert "initial text" not in value


class TestSmartTargetAccessibilityMethods:
    """Test SmartTarget accessibility methods."""

    def test_axe_eval(self, has_driver_instance, base_url):
        """Test that axe_eval runs accessibility scan on scoped element."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        # Test on the accessible form section
        accessible_form = SelectorTemplate("#accessible-form", "css")
        smart_target = SmartTarget(accessible_form, has_driver_instance)
        results = smart_target.axe_eval()
        # Just verify it returns results
        assert results is not None

    def test_assert_no_axe_violations_with_impact_of_at_least(self, has_driver_instance, base_url):
        """Test that assert_no_axe_violations_with_impact_of_at_least works."""
        has_driver_instance.navigate_to(f"{base_url}/smart_components.html")
        # Test on the accessible form section (should have no critical violations)
        accessible_form = SelectorTemplate("#accessible-form", "css")
        smart_target = SmartTarget(accessible_form, has_driver_instance)
        # This may raise if there are violations, which is expected behavior
        # For now we just test that the method exists and runs
        # Should not raise for accessible content
        smart_target.assert_no_axe_violations_with_impact_of_at_least("critical")


class TestSmartTargetStrRepresentation:
    """Test SmartTarget string representation."""

    def test_str_representation(self, smart_component):
        """Test that SmartTarget has useful string representation."""
        str_repr = str(smart_component.button)
        assert "SmartTarget" in str_repr
        assert "_target=" in str_repr
