---
description: Add a new test method to an existing Galaxy Selenium test file
---

The user input can be provided directly or as a command argument - you **MUST** consider it before proceeding.

User input:

$ARGUMENTS

## Context

You are adding a new test method to an existing Selenium test file in the Galaxy test suite. Read the CLAUDE.md file in this directory for complete context on Galaxy Selenium testing conventions.

## Task

Add one or more new test methods to an existing test file based on the user's description. The user should specify:
- Which test file to modify (e.g., `test_history_panel.py`)
- What scenario(s) to test
- Any special requirements (managed history, admin access, etc.)

## Requirements

1. **Read CLAUDE.md** in the current directory for full context

2. **Read the target test file** to understand:
   - Existing class structure and attributes
   - Import statements already present
   - Coding style and patterns used
   - Helper methods defined in the class

3. **Match the existing style**:
   - Use same patterns as other methods in the class
   - Follow same naming conventions
   - Maintain consistent indentation and spacing
   - Add similar docstrings

4. **Add necessary imports** if new decorators/modules are needed:
   - `managed_history` if using `@managed_history`
   - `requires_admin` if using `@requires_admin`
   - Any other decorators from `galaxy.selenium.navigates_galaxy`

5. **Use appropriate decorators**:
   - Always use `@selenium_test`
   - Add `@managed_history` if the test needs predictable HIDs
   - Add `@requires_admin` if testing admin features
   - Add `@edit_details` or other navigation decorators as needed

6. **Follow test structure**:
   - Clear, descriptive method name: `test_<specific_scenario>`
   - Docstring explaining what is being tested
   - Proper setup and navigation
   - Clear assertions
   - Screenshots if helpful (use `self.screenshot("description")`)

7. **Respect class attributes**:
   - If class has `ensure_registered = True`, user is already logged in
   - If class has `run_as_admin = True`, tests run as admin
   - Use these to simplify test setup

## Output

1. **Confirm the target**:
   - Which file will be modified
   - What test method(s) will be added

2. **Add the test method(s)** to the appropriate class

3. **Update imports** if needed

4. **Explain what was added**:
   - What the new test does
   - Why certain decorators were used
   - How it fits with existing tests
   - How to run just this new test

## Example Usage

```
/add-test Add a test for tag filtering to test_history_panel.py
/add-test Add admin test for user deletion to test_admin_app.py
/add-test Add dataset copy test with managed history to test_dataset_edit.py
```

## Notes

- Always read the existing file first to match its style
- Don't duplicate existing test scenarios
- Keep tests independent and focused
- Consider edge cases and error conditions
- Add accessibility tests where appropriate
