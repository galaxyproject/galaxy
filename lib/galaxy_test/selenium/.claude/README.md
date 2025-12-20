# Claude Code Configuration for Galaxy Selenium Tests

This directory contains Claude Code configuration and slash commands for working with Galaxy's Selenium test suite.

## CLAUDE.md

The `CLAUDE.md` file in the parent directory (`../CLAUDE.md`) provides comprehensive documentation about Galaxy Selenium testing conventions. It includes:

- Test structure and base classes
- Common patterns (login, navigation, data upload)
- Decorator usage (`@selenium_test`, `@managed_history`, `@requires_admin`)
- Component system access
- Helper methods and wait types
- Accessibility testing guidelines
- Complete test templates for different scenarios

**Purpose**: This file serves as context for Claude Code when writing or modifying Selenium tests, ensuring consistency with Galaxy's testing conventions.

## Slash Commands

### Direct Test Creation

#### `/new-selenium-test`

Bootstrap a new Selenium test file from scratch.

**Usage:**
```
/new-selenium-test <feature description>
```

**Examples:**
```
/new-selenium-test workflow import with accessibility testing
/new-selenium-test admin user management features
/new-selenium-test dataset metadata editing with managed history
```

**What it does:**
- Creates a new test file with proper structure
- Includes appropriate imports and decorators
- Follows Galaxy naming conventions
- Uses correct template based on requirements
- Asks clarifying questions if needed

#### `/add-selenium-test`

Add new test methods to an existing Selenium test file.

**Usage:**
```
/add-selenium-test <description and target file>
```

**Examples:**
```
/add-selenium-test Add a test for tag filtering to test_history_panel.py
/add-selenium-test Add admin test for user deletion to test_admin_app.py
/add-selenium-test Add dataset copy test with managed history to test_dataset_edit.py
```

**What it does:**
- Reads existing file to match style
- Adds properly structured test methods
- Updates imports if necessary
- Maintains consistency with existing code

### Interactive Jupyter Workflow

For complex tests or when you need to explore the DOM interactively, use the Jupyter notebook workflow:

#### `/setup-selenium-test-notebook`

Create a Jupyter notebook for interactively prototyping a Selenium test.

**Usage:**
```
/setup-selenium-test-notebook <feature description OR GitHub PR>
```

**Examples (text mode):**
```
/setup-selenium-test-notebook dataset metadata editing
/setup-selenium-test-notebook workflow import from URL
/setup-selenium-test-notebook admin user quota management
```

**Examples (GitHub PR mode):**
```
/setup-selenium-test-notebook https://github.com/galaxyproject/galaxy/pull/12345
/setup-selenium-test-notebook #12345
/setup-selenium-test-notebook 12345
```

**What it does:**
- Fetches PR context (if PR mode): description, screenshots, author
- Launches research subagent to find similar existing tests
- Creates a prototype notebook in `jupyter/` directory
- Includes PR context, example code, and starter code
- Prints complete setup instructions

**Workflow:**
1. Run `/setup-selenium-test-notebook <feature>` to create notebook
2. Follow printed instructions to start Jupyter
3. Prototype test interactively with screenshots and documentation
4. Use `screenshot("name", caption="...")` to add captioned screenshots
5. Use `document("markdown")` to add narrative documentation
6. Run `/extract-selenium-test` when done to convert to test file

#### `/extract-selenium-test`

Extract test code from a Jupyter notebook and convert to a proper test file.

**Usage:**
```
/extract-selenium-test <notebook path or description>
```

**Examples:**
```
/extract-selenium-test from jupyter/test_prototype_dataset_metadata.ipynb
/extract-selenium-test jupyter/test_prototype_workflow_import.ipynb as test_workflow_import
/extract-selenium-test notebook test_prototype_admin_users.ipynb
```

**What it does:**
- Reads notebook cells (skipping initialization)
- Transforms `gx_selenium_context` to `self`
- Detects required decorators and attributes
- Creates properly structured Pytest test file for the Selenium test suite
- Groups related cells into test methods

## Getting Started

### Quick Start (Direct Creation)

For straightforward tests with known requirements:

1. **Read `../CLAUDE.md`** to understand Galaxy Selenium testing conventions
2. **Use `/new-selenium-test <description>`** to create a new test file
3. **Use `/add-selenium-test <description>`** to extend an existing test file
4. **Run** with `pytest lib/galaxy_test/selenium/test_<your_file>.py`

### Interactive Development (Jupyter Workflow)

For complex tests or DOM exploration:

1. **Create notebook**: `/setup-selenium-test-notebook <description>`
2. **Start Galaxy & Jupyter** following the printed instructions
3. **Prototype interactively** in the notebook with live screenshots
4. **Add documentation** using `screenshot(caption="...")` and `document("markdown")`
5. **Extract to test**: `/extract-selenium-test <notebook_path>`
6. **Run** with `pytest lib/galaxy_test/selenium/test_<your_file>.py`

## Test Stories

Test stories provide visual narrative documentation of test execution, automatically generating markdown, HTML, and PDF artifacts with interleaved screenshots and documentation.

### Enabling Test Stories

Set the `GALAXY_TEST_STORIES_DIRECTORY` environment variable:

```bash
export GALAXY_TEST_STORIES_DIRECTORY=/path/to/stories
pytest lib/galaxy_test/selenium/test_your_feature.py
```

### Generated Artifacts

For each test, a timestamped directory is created containing:
- `story.md` - Markdown source with embedded screenshots
- `story.html` - Self-contained HTML with embedded images
- `story.pdf` - PDF version (if weasyprint available)
- `{test_name}.zip` - Zip archive of all artifacts

### Building Stories in Tests

Use `screenshot()` with captions and `document()` to create rich test documentation:

```python
@selenium_test
def test_workflow_import(self):
    self.document("## Testing TRS Import\n\nThis test validates workflow import from TRS.")
    
    self.navigate_to_workflows()
    self.screenshot("workflow_list", caption="Initial workflow listing")
    
    self.document("Import workflow from TRS endpoint...")
    self.import_workflow_from_trs("https://...")
    self.screenshot("after_import", caption="Workflow appears in listing after import")
```

## Tips

- **Be specific** in command descriptions (mention admin access, managed history, etc.)
- **Use Jupyter workflow** when you need to explore the DOM or iterate quickly
- **Use direct creation** when you know exactly what needs to be tested
- Commands will **ask clarifying questions** if your request is ambiguous
- **Review generated code** to ensure it meets your specific needs
- **Reference existing tests** in the parent directory for patterns and examples
