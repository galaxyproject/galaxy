---
description: Bootstrap a new Galaxy Selenium test file with proper structure and conventions
---

The user input can be provided directly or as a command argument - you **MUST** consider it before proceeding.

User input:

$ARGUMENTS

## Context

You are creating a new Selenium test file for the Galaxy web application. Read the CLAUDE.md file in this directory for complete context on:
- Test structure and conventions
- Available decorators and their purposes
- Common patterns and helper methods
- Component system usage
- Example templates

## Task

Create a new Selenium test file based on the user's description. The user may specify:
- Feature name (e.g., "dataset permissions", "workflow import")
- Test scenarios to include
- Whether it needs admin access (`run_as_admin = True`)
- Whether it needs managed history (`@managed_history`)
- Accessibility testing requirements

## Requirements

1. **Read CLAUDE.md** in the current directory for full context on Galaxy Selenium testing conventions

2. **Determine the appropriate template** based on requirements:
   - Basic test (most common)
   - Test with managed history (for predictable dataset HIDs)
   - Admin test (requires `run_as_admin = True`)
   - Combination of the above

3. **Generate the test file** with:
   - Proper imports from `.framework`
   - Class name following `Test<FeatureName>` convention
   - Appropriate class attributes (`ensure_registered`, `run_as_admin`)
   - Well-named test methods using `test_<scenario>` pattern
   - Proper decorators (`@selenium_test`, `@managed_history`, `@requires_admin`)
   - Docstrings for each test method
   - Common patterns from existing tests

4. **File naming**: `test_<feature_name>.py` (lowercase with underscores)

5. **Include common elements**:
   - Navigation (`self.home()`)
   - Component access via `self.components.*`
   - Proper wait/sleep patterns
   - Assertions (`self.assert_no_error_message()`, etc.)
   - Accessibility tests where appropriate

6. **For dataset/history tests**:
   - Use `@managed_history` decorator
   - Upload test data with `self.perform_upload(self.get_filename("1.txt"))`
   - Wait for datasets with `self.history_panel_wait_for_hid_ok(hid)`
   - Reference datasets by predictable HID (1, 2, 3...)

7. **For admin tests**:
   - Add `run_as_admin = True` class attribute
   - Use `@requires_admin` decorator
   - Include `self.admin_login()` and `self.admin_open()`
   - Import from `galaxy_test.base.decorators import requires_admin`

8. **Best practices**:
   - Keep tests focused and independent
   - Use descriptive test method names
   - Add comments for complex interactions
   - Follow existing code style in this directory
   - Consider accessibility testing (`assert_no_axe_violations_with_impact_of_at_least`)

## Output

1. **Ask clarifying questions** if the user's request is ambiguous:
   - Does this need admin access?
   - Does this need managed history for dataset testing?
   - What specific scenarios should be tested?
   - Should accessibility testing be included?

2. **Create the test file** at `/Users/jxc755/workspace/galaxy/lib/galaxy_test/selenium/test_<feature_name>.py`

3. **Explain the structure**:
   - Which template was used and why
   - Key components and patterns included
   - How to run the test
   - Any additional setup needed

## Example Usage

```
/new-test workflow import with accessibility testing
/new-test admin user management features
/new-test dataset metadata editing with managed history
```

## Notes

- Reference CLAUDE.md for comprehensive examples and patterns
- Look at similar existing tests in this directory for inspiration
- Ensure all imports are correct and from the right modules
- The test should be immediately runnable with pytest
