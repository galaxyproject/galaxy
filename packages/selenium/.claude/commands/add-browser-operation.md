---
description: Add a new low-level browser operation to both Selenium and Playwright implementations with tests
---

## User Input

```text
$ARGUMENTS
```

**Operation Description**: The user input describes the browser operation to add (e.g., "add method to scroll element to center of viewport" or "add method to get element's bounding box").

## Implementation Steps

1. **Parse the operation description** from user input:
   - Extract the operation name (convert to snake_case method name)
   - Identify parameters needed
   - Determine return type
   - Understand the browser behavior to implement

2. **Add to HasDriverProtocol** (`lib/galaxy/selenium/has_driver_protocol.py`):
   - Add abstract method with proper signature
   - Include comprehensive docstring with:
     * Description of what the operation does
     * Args documentation
     * Returns documentation
     * Usage example if helpful
   - Add `ContextManager` import if method returns a context manager

3. **Implement in HasDriver** (`lib/galaxy/selenium/has_driver.py`):
   - Implement using Selenium WebDriver API
   - Use `self.driver` for page-level operations
   - Use element methods for element-specific operations
   - Handle any Selenium-specific quirks or edge cases
   - Add appropriate error handling

4. **Implement in HasPlaywrightDriver** (`lib/galaxy/selenium/has_playwright_driver.py`):
   - Implement using Playwright API
   - Use `self.page` for page-level operations
   - For element operations, follow the wrapper pattern:
     * Create public method accepting `WebElementProtocol`
     * Use `self._unwrap_element()` to get `ElementHandle`
     * Create private `_method_name()` with `ElementHandle` parameter
   - Use `self._frame_or_page` instead of `self.page` if operation should work within frames
   - Handle any Playwright-specific patterns

5. **Update HasDriverProxy** (`lib/galaxy/selenium/has_driver_proxy.py`):
   - Add delegation method that forwards to `self._driver_impl`
   - Include docstring (can be brief, main docs are in protocol)
   - Ensure type hints match the protocol

6. **Add comprehensive unit tests** (`test/unit/selenium/test_has_driver.py`):
   - Create new test class or add to existing relevant class
   - Test the operation with `has_driver_instance` fixture (parametrized for both backends)
   - Include tests for:
     * Basic functionality
     * Edge cases
     * Error conditions if applicable
     * Different element states if relevant
   - Use `base_url` fixture to load test pages
   - Assert expected behavior for both Selenium and Playwright

7. **Verify implementation**:
   - Run tests: `uv run pytest tests/seleniumtests/test_has_driver.py::<TestClass>::<test_name> -v`
   - Run type checking: `make mypy`
   - Ensure all 3 backend variants pass (selenium, playwright, proxy-selenium)

8. **Update WebElementProtocol if needed**:
   - If the operation is element-specific and should be callable on elements directly
   - Add to `lib/galaxy/selenium/web_element_protocol.py`
   - Implement in `lib/galaxy/selenium/playwright_element.py` for Playwright
   - Selenium's WebElement will implement it natively if it's a standard method

## Example Workflow

For operation "get element's computed background color":

1. **Protocol** (`has_driver_protocol.py`):
```python
@abstractmethod
def get_element_background_color(self, element: WebElementProtocol) -> str:
    """Get the computed background color of an element.

    Args:
        element: The element to get background color from

    Returns:
        The computed background-color CSS value (e.g., "rgb(255, 0, 0)")
    """
    ...
```

2. **Selenium** (`has_driver.py`):
```python
def get_element_background_color(self, element: WebElementProtocol) -> str:
    return element.value_of_css_property("background-color")
```

3. **Playwright** (`has_playwright_driver.py`):
```python
def get_element_background_color(self, element: WebElementProtocol) -> str:
    return element.value_of_css_property("background-color")
```

4. **Proxy** (`has_driver_proxy.py`):
```python
def get_element_background_color(self, element: WebElementProtocol) -> str:
    """Get the computed background color of an element."""
    return self._driver_impl.get_element_background_color(element)
```

5. **Tests** (`test_has_driver.py`):
```python
class TestCSSProperties:
    def test_get_element_background_color(self, has_driver_instance, base_url):
        has_driver_instance.navigate_to(f"{base_url}/basic.html")
        element = has_driver_instance.find_element_by_id("test-div")
        color = has_driver_instance.get_element_background_color(element)
        assert color != ""
        # Color format varies by browser, just check it's a valid value
        assert isinstance(color, str)
```

## Notes

- Always maintain API compatibility between Selenium and Playwright implementations
- Use the wrapper pattern (`_unwrap_element()`) for element operations in Playwright
- Ensure both implementations have identical behavior from the user's perspective
- Write thorough tests that verify behavior on both backends
- Follow existing code patterns and naming conventions
