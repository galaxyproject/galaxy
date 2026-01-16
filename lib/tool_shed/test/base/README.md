# Test Infrastructure

Base classes and utilities for Tool Shed functional tests.

## Components

```
base/
├── driver.py           # ToolShedTestDriver - embedded server setup
├── twilltestcase.py    # ShedTwillTestCase - main test base class
├── playwrighttestcase.py # PlaywrightTestCase - browser test base
├── playwrightbrowser.py  # PlaywrightShedBrowser - browser abstraction
├── twillbrowser.py     # TwillShedBrowser - legacy browser
├── browser.py          # ShedBrowser protocol
├── populators.py       # ToolShedPopulator - API fixture creation
├── api.py              # ShedApiTestCase - API test base
├── api_util.py         # API interaction utilities
└── test_db_util.py     # Direct database access
```

## Base Classes

### ShedTwillTestCase

Main test base class with repository/category management:

```python
class TestFeature(ShedTwillTestCase):
    def test_repo_creation(self):
        category = self.create_category(name="Tools")
        repo = self.get_or_create_repository(
            name="mytool",
            category=category,
            strings_displayed=["created"],
        )
        self.upload_file(repo, "mytool.tar")
```

Key methods:
- `create_category()` - Create test category
- `get_or_create_repository()` - Create repository with category
- `upload_file()` / `commit_tar_to_repository()` - Upload content
- `reset_metadata_on_repository()` - Reset repository metadata
- `verify_installed_repository()` - Check Galaxy installation

### PlaywrightTestCase

For browser UI tests:

```python
class TestUI(PlaywrightTestCase):
    def test_navigation(self):
        self.visit_url("/")
        page = self._page  # Playwright Page object
        page.click(".nav-link")
        self.screenshot("after_click")  # Optional screenshot
```

Properties:
- `_page` - Playwright Page instance
- `_playwright_browser` - PlaywrightShedBrowser wrapper

### ShedApiTestCase

Pure API tests without browser:

```python
class TestApi(ShedApiTestCase):
    def test_endpoint(self):
        response = self._get("repositories")
        assert response.status_code == 200
```

## ToolShedPopulator

API-based fixture creation (in `populators.py`):

```python
populator = ToolShedPopulator(admin_interactor, user_interactor)

# Create category
category = populator.new_category("Test Category")

# Create and populate repository
repo = populator.new_repository(category_id=category.id)
populator.upload_revision(repo, "column_maker")  # From test_data/repos/

# Setup predefined repos
populator.setup_column_maker_repo()
populator.setup_bismark_repo()
```

### Upload Methods

```python
# Upload from test_data/repos/ directory
populator.upload_revision(repo, "column_maker")

# Upload specific tar file
populator.upload_tar(repo, path_to_tar)

# Upload multiple revisions
for revision in ["1", "2", "3"]:
    populator.upload_revision(repo, f"column_maker/{revision}")
```

## Browser Abstractions

### ShedBrowser Protocol

Common interface for browser implementations:

```python
class ShedBrowser(Protocol):
    def visit_url(self, url: str) -> None: ...
    def check_page_for_string(self, string: str) -> None: ...
    def submit_form(self, button: str, **kwd) -> None: ...
```

### PlaywrightShedBrowser

Modern browser with Playwright:

```python
browser = PlaywrightShedBrowser(page)
browser.visit_url("/")
browser.logout_if_logged_in()
browser.expect_logged_in()
```

Locators available via `Locators` class:
- `Locators.toolbar_login`
- `Locators.login_submit_button`
- `Locators.register_link`

### TwillShedBrowser

Legacy browser using Twill library (deprecated, use Playwright).

## Test Driver

`ToolShedTestDriver` sets up embedded shed server:

```python
# Usually handled by conftest.py fixture
driver = ToolShedTestDriver()
driver.setup()  # Starts embedded server
# ... run tests ...
driver.tear_down()
```

The `embedded_driver` fixture in `conftest.py` manages this automatically.

## Database Utilities

Direct database access via `test_db_util.py`:

```python
from tool_shed.test.base import test_db_util

# Get repository by name
repo = test_db_util.get_repository_by_name("myrepo")

# Get user
user = test_db_util.get_user("test@example.org")
```

Use sparingly - prefer API-based approaches via populators.
