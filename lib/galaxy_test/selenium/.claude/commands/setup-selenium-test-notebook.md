---
description: Create a Jupyter notebook for interactively prototyping a new Selenium test
---

The user input can be provided directly or as a command argument - you **MUST** consider it before proceeding.

User input:

$ARGUMENTS

## Context

Galaxy Selenium tests can be prototyped interactively in Jupyter notebooks. The notebook environment provides:
- Full access to the Selenium test infrastructure
- Screenshot capabilities with inline display
- Interactive DOM exploration
- Rapid iteration without restarting Galaxy or re-running costly intermediate steps such as data upload.

This command supports two modes:
1. **Text description** - User provides a feature description
2. **GitHub PR** - User provides a PR URL or number (fetches description and screenshots)

## Task

Create a new Jupyter notebook for prototyping a Selenium test. Input can be:
- A text description of the feature
- A GitHub PR URL (e.g., `https://github.com/galaxyproject/galaxy/pull/12345`)
- A PR number (e.g., `#12345` or `12345`)

## Requirements

1. **Determine input mode**:
   - If input contains GitHub URL or PR number (#), use PR mode
   - Otherwise, use text description mode

2. **PR Mode - Fetch PR information** (if applicable):
   - Use `gh pr view <number> --json title,body,author` to get PR metadata
   - Extract feature description from PR title and body
   - Look for screenshots in PR body (markdown image syntax)
   - If screenshots found, note their URLs for reference in notebook
   - Use PR description as basis for feature understanding

3. **Research similar tests** - Do a quick search in this directory only:
   - Use Glob to find test files: `*.py` in current directory
   - Use Grep to search for keywords related to the feature
   - Read 1-2 most relevant test files
   - Extract key patterns: component usage, helper methods, decorators
   - Note which components are used (e.g., `self.components.history_panel.*`)
   - Keep this step fast and focused

4. **Create the notebook file** at `jupyter/test_prototype_<feature_name>.ipynb` with 4-5 cells:

   **Cell 1** (tagged 'parameters'):
   ```python
   # Cell is tagged with 'parameters' so it can be parameterized with papermill,
   # if config not overridden ./galaxy_selenium_context.yml can also be populated.
   config = None
   ```

   **Cell 2** (initialization):
   ```python
   from galaxy_test.selenium.jupyter_context import init
   gx_selenium_context = init(config)
   ```

   **Cell 3** (PR context - ONLY if PR mode):
   ```python
   # Testing PR #<number>: <PR title>
   # Author: <author>
   #
   # Description:
   # <PR body text>
   #
   # Screenshots in PR:
   # - <screenshot URL 1>
   # - <screenshot URL 2>
   #
   # You can compare your gx_selenium_context.screenshot() output with PR screenshots
   ```

   **Cell 4** (reference examples from similar tests):
   ```python
   # Similar test examples for reference:
   #
   # From test_<similar_file_1>.py:
   # <relevant code snippets showing component usage>
   #
   # From test_<similar_file_2>.py:
   # <more relevant code snippets>
   #
   # Components available:
   # - self.components.<component_name>.<method>
   # [List relevant components based on research]
   ```

   **Cell 5** (test prototype - add helpful starter code):
   ```python
   # Prototype your test here
   # gx_selenium_context provides all the methods from SeleniumTestCase

   # Example starter code based on feature description
   ```

5. **Add starter code** to the final cell based on the feature requirements:
   - Login if needed: `gx_selenium_context.login()`
   - Navigation: `gx_selenium_context.home()`
   - Dataset creation if needed: `gx_selenium_context.dataset_populator.new_dataset(history_id)`
   - Screenshots: `gx_selenium_context.screenshot("description")`
   - Admin access if needed: `gx_selenium_context.admin_login()`
   - Component access examples
   - Comments suggesting what to implement

6. **Check configuration** - Verify `jupyter/galaxy_selenium_context.yml` exists:
   - If missing, inform user to copy from `galaxy_selenium_context.yml.sample`
   - Explain they need to configure `login_email`, `login_password`, and optionally `admin_api_key`

## Implementation Steps

1. **Detect input mode and fetch PR if needed**:
   - Check if input contains PR URL or number
   - If PR mode: Use `gh pr view <number> --json title,body,author` to fetch PR data
   - Extract feature description from PR content
   - Parse PR body for screenshot URLs (markdown image syntax: `![...](url)`)

2. **Search for similar tests** directly (no subagent):
   - Use Grep to search for keywords in test files in current directory
   - Example: search for "storage", "dashboard", "chart", etc. based on feature
   - Identify 1-2 relevant files from grep results
   - Read those files
   - Extract key patterns: decorators used, components accessed, helper methods called
   - Identify relevant code snippets (5-15 lines) showing component usage
   - Keep this fast - just find the most obviously related tests

3. **Create the notebook file** with:
   - Standard initialization cells
   - PR context cell (if PR mode)
   - Similar test examples cell
   - Starter code cell

4. **Print setup instructions**:
   ```
   ✓ Created prototype notebook: jupyter/test_prototype_<feature_name>.ipynb
   [If PR mode: ✓ Loaded context from PR #<number>: <title>]
   [If PR mode: ✓ Found <N> screenshots in PR for reference]

   To start prototyping:

   1. Ensure Galaxy is running:
      Terminal 1: GALAXY_SKIP_CLIENT_BUILD=1 GALAXY_RUN_WITH_TEST_TOOLS=1 sh run.sh
      Terminal 2: make client-dev-server

   2. Check configuration (first time only):
      - Copy jupyter/galaxy_selenium_context.yml.sample to jupyter/galaxy_selenium_context.yml
      - Edit it with your test user credentials and admin API key

   3. Start Jupyter (from repo root):
      . .venv/bin/activate
      pip install jupyter  # first time only
      make serve-selenium-notebooks

   4. Open the notebook in Jupyter:
      jupyter/test_prototype_<feature_name>.ipynb

   5. Run cells interactively to prototype your test
      - Screenshots will display inline
      - You can inspect the DOM, try different selectors
      - Iterate quickly without restarting
      - Components selectors defined in lib/galaxy/navigation/navigation.yml
        will be dynamically reloaded in this mode.

   6. When done, use /extract-test to convert to a test file
   ```

## Example Usage

**Text description mode:**
```
/setup-selenium-test-notebook dataset metadata editing
/setup-selenium-test-notebook workflow import from URL
/setup-selenium-test-notebook admin user quota management
```

**GitHub PR mode:**
```
/setup-selenium-test-notebook https://github.com/galaxyproject/galaxy/pull/12345
/setup-selenium-test-notebook #12345
/setup-selenium-test-notebook 12345
```

## Notes

- The notebook uses `JupyterTestContextImpl` which provides the "same" interface as `SeleniumTestCase`
- All methods from `NavigatesGalaxy` are available on `gx_selenium_context`
- Screenshots are displayed inline in Jupyter for immediate feedback
- Configuration is read from `jupyter/galaxy_selenium_context.yml` if present
- After prototyping, use `/extract-test` to convert notebook cells into a proper test file
