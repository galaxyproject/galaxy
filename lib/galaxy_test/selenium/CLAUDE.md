# Galaxy Selenium Test Suite

This directory contains Selenium-based end-to-end tests for the Galaxy web interface.

## Test Structure

All Selenium tests follow these conventions:

### Base Class and Decorators

```python
from .framework import (
    selenium_test,
    SeleniumTestCase,
)

class TestYourFeature(SeleniumTestCase):
    @selenium_test
    def test_your_scenario(self):
        # Test implementation
```

### Key Components

- **Base class**: All test classes inherit from `SeleniumTestCase`
- **Test decorator**: All test methods use the `@selenium_test` decorator
- **Framework module**: `framework.py` provides the base testing infrastructure
- **Component system**: Use `self.components` to access page object selectors

## Common Patterns

### User Registration and Login

```python
# Ensure user is registered before running tests
class TestYourFeature(SeleniumTestCase):
    ensure_registered = True  # Add this class attribute

    # Or register manually in a test
    @selenium_test
    def test_with_login(self):
        email = self._get_random_email()
        self.register(email)
        self.submit_login(email, assert_valid=True)
```

### Navigation

```python
self.home()  # Navigate to home page
self.history_panel_wait_for_history_loaded()  # Wait for history to load
```

### Component Access

```python
# Access UI components via the component system
self.components.masthead.login_masthead_button.wait_for_and_click()
self.components.history_panel.name_edit_input.wait_for_visible()
```

### Accessibility Testing

```python
# Test for accessibility violations
self.components.login.form.assert_no_axe_violations_with_impact_of_at_least("moderate")

# With exceptions for specific rules
VIOLATION_EXCEPTIONS = ["heading-order", "label"]
self.components.history_panel._.assert_no_axe_violations_with_impact_of_at_least(
    "moderate", VIOLATION_EXCEPTIONS
)
```

### Data Upload

```python
# Upload test data
self.perform_upload(self.get_filename("1.txt"))
self.wait_for_history()

# Wait for specific dataset
self.history_panel_wait_for_hid_ok(1)
```

### Assertions with Retry Logic

```python
from .framework import retry_assertion_during_transitions

@retry_assertion_during_transitions
def assert_something(self):
    # Assertion that might fail during UI transitions
    assert condition
```

### Fresh History with @managed_history

Use the `@managed_history` decorator when you need a clean history for your test. This ensures predictable HIDs (History Item IDs) for uploaded datasets, starting from 1.

```python
from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)

class TestHistoryFeature(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_with_fresh_history(self):
        # Upload files with predictable HIDs
        self.perform_upload(self.get_filename("1.txt"))
        self.history_panel_wait_for_hid_ok(1)  # First upload is HID 1

        self.perform_upload(self.get_filename("2.txt"))
        self.history_panel_wait_for_hid_ok(2)  # Second upload is HID 2

        # Now you can reliably reference datasets by HID
        self.history_panel_click_item_title(hid=1, wait=True)
```

**Key benefits of @managed_history:**
- Creates a fresh history before the test runs
- HIDs start at 1 and increment predictably
- No interference from previous test data
- Makes tests more reliable and maintainable

### Testing Admin Functionality

For tests that require admin access, add `run_as_admin = True` as a class attribute and use the `@requires_admin` decorator:

```python
from galaxy_test.base.decorators import requires_admin
from .framework import (
    selenium_test,
    SeleniumTestCase,
)

class TestAdminFeature(SeleniumTestCase):
    run_as_admin = True  # This makes the test run with admin privileges

    @selenium_test
    @requires_admin
    def test_admin_functionality(self):
        self.admin_login()  # Login as admin user
        self.admin_open()   # Navigate to admin panel

        # Access admin components
        admin_component = self.components.admin
        admin_component.index.some_feature.wait_for_and_click()

        # Test admin-specific functionality
```

**Admin test requirements:**
- `run_as_admin = True` class attribute
- `@requires_admin` decorator on test methods
- Use `self.admin_login()` to authenticate as admin
- Use `self.admin_open()` to navigate to admin panel

## File Naming

- Test files: `test_<feature_name>.py`
- Test classes: `Test<FeatureName>`
- Test methods: `test_<specific_scenario>`

## Helper Methods Available

Common methods from `SeleniumTestCase`:

- `self.home()` - Navigate to home
- `self.register(email, password=None)` - Register new user
- `self.submit_login(email, password=None, assert_valid=True)` - Login
- `self.logout_if_needed()` - Logout if logged in
- `self.is_logged_in()` - Check login status
- `self.assert_error_message()` - Assert error message displayed
- `self.assert_no_error_message()` - Assert no error message
- `self._get_random_email()` - Generate random test email
- `self._get_random_name(prefix="")` - Generate random name
- `self.sleep_for(wait_type)` - Sleep for specified wait type
- `self.wait_for_history()` - Wait for history panel to load
- `self.perform_upload(filepath)` - Upload a file
- `self.history_panel_wait_for_hid_ok(hid)` - Wait for dataset to be OK

## Wait Types

```python
self.sleep_for(self.wait_types.UX_RENDER)       # UI rendering delay
self.sleep_for(self.wait_types.UX_TRANSITION)   # UI transition delay
```

## Test Data Files

- Test data files are accessed via `self.get_filename("filename")`
- Common test files include simple text files, tabular data, etc.

## Example Test Templates

### Basic Test Template

```python
from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class TestNewFeature(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    def test_basic_scenario(self):
        """Test description goes here."""
        self.home()
        # Test implementation
        self.assert_no_error_message()

    @selenium_test
    def test_accessibility(self):
        """Test accessibility compliance."""
        self.components.your_feature._.assert_no_axe_violations_with_impact_of_at_least("moderate")
```

### Template with Managed History

```python
from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)


class TestDatasetFeature(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_with_datasets(self):
        """Test with predictable dataset HIDs."""
        # Upload test data
        self.perform_upload(self.get_filename("1.txt"))
        self.history_panel_wait_for_hid_ok(1)

        # Interact with dataset by HID
        self.history_panel_click_item_title(hid=1, wait=True)
        # Further test logic...
```

### Admin Test Template

```python
from galaxy_test.base.decorators import requires_admin
from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class TestAdminFeature(SeleniumTestCase):
    run_as_admin = True

    @selenium_test
    @requires_admin
    def test_admin_panel(self):
        """Test admin functionality."""
        self.admin_login()
        self.admin_open()

        admin_component = self.components.admin
        # Test admin-specific features...
```

## Additional Resources

- `framework.py` - Base test framework and utilities
- `conftest.py` - Pytest fixtures and configuration
- `jupyter_context.py` - Jupyter notebook testing utilities
- Page objects and navigation helpers are in `galaxy.selenium.navigates_galaxy`
