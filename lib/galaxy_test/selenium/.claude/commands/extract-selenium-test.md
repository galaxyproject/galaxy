---
description: Extract test code from a Jupyter notebook and convert it to a proper Selenium test file
---

The user input can be provided directly or as a command argument - you **MUST** consider it before proceeding.

User input:

$ARGUMENTS

## Context

After prototyping a Selenium test interactively in a Jupyter notebook, this command extracts the test code and converts it into a proper test file following Galaxy's Selenium testing conventions.

## Task

Extract test cells from a Jupyter notebook and create a properly structured Selenium test file.

## Requirements

1. **Read the target notebook** specified by the user (e.g., `jupyter/test_prototype_<name>.ipynb`)

2. **Read CLAUDE.md** for full context on Galaxy Selenium test conventions

3. **Identify test cells** - Extract all cells after the initialization cell (cell 2):
   - Skip the parameters cell (cell 0)
   - Skip the initialization cell (cell 1)
   - Extract cells 2+ which contain the test implementation

4. **Transform notebook code to test code**:
   - Replace `gx_selenium_context.` with `self.`
   - Remove screenshot calls or keep them if desired for debugging
   - Group related operations into logical test methods
   - Add proper decorators (`@selenium_test`, `@managed_history`, etc.)
   - Add docstrings to test methods

5. **Determine test structure** from the notebook code:
   - Does it need `ensure_registered = True`? (if it calls `register()` or `login()`)
   - Does it need `run_as_admin = True`? (if it calls `admin_login()`)
   - Does it need `@managed_history`? (if it works with datasets/HIDs)
   - Does it need `@requires_admin`? (if testing admin features)

6. **Create proper test file**:
   - Add appropriate imports
   - Create test class with correct name
   - Add class attributes as needed
   - Create test methods from notebook cells
   - Group related cells into single test methods
   - Split unrelated operations into separate test methods

7. **Handle special cases**:
   - If notebook uses `dataset_populator`, keep those patterns
   - If notebook uses `current_history_id()`, consider `@managed_history`
   - If notebook has multiple distinct scenarios, create multiple test methods
   - Convert inline assertions to proper pytest assertions

8. **File naming**: Ask user for feature name if not clear from notebook name

## Output

1. **Analyze the notebook** and report:
   - Number of test cells found
   - Key operations detected (login, upload, navigation, etc.)
   - Recommended test structure (basic/managed history/admin)

2. **Ask for confirmation** if structure is ambiguous:
   - Should this be one test method or multiple?
   - What should the test methods be named?
   - Should screenshots be kept or removed?

3. **Create the test file** at `test_<feature_name>.py` with:
   - Proper imports
   - Correctly structured test class
   - Appropriate decorators and attributes
   - Well-named test methods with docstrings
   - Transformed code (gx_selenium_context → self)

4. **Report completion**:
   ```
   ✓ Extracted test from notebook: jupyter/test_prototype_<name>.ipynb
   ✓ Created test file: test_<feature_name>.py

   Test structure:
   - Class: Test<FeatureName>
   - Attributes: [ensure_registered, run_as_admin, etc.]
   - Methods: test_method_1, test_method_2, ...

   To run the test:
   pytest lib/galaxy_test/selenium/test_<feature_name>.py

   Or run a specific test:
   pytest lib/galaxy_test/selenium/test_<feature_name>.py::Test<FeatureName>::test_method_1
   ```

5. **Provide review guidance**:
   - Suggest reviewing for proper wait/sleep patterns
   - Recommend adding assertions if few were found
   - Suggest accessibility testing if not present
   - Note any hardcoded values that should be parameterized

## Example Usage

```
/extract-test from jupyter/test_prototype_dataset_metadata.ipynb
/extract-test jupyter/test_prototype_workflow_import.ipynb as test_workflow_import
/extract-test notebook test_prototype_admin_users.ipynb
```

## Notes

- Read CLAUDE.md for complete context on test conventions
- The notebook's initialization cells (0-1) are never included in the test
- Multiple notebook cells can be combined into a single test method if related
- Distinct scenarios should become separate test methods
- The command should intelligently detect patterns (admin, managed history, etc.)
- Preserve the logic but adapt to test framework conventions
- Remove debug-only code (print statements, excessive screenshots)
- Keep test-relevant screenshots if they help document expected states
