# Tool Shed Functional Tests

Integration and browser tests for the Tool Shed. Requires a running server.

## Running Tests

```shell
# From packages/tool_shed directory

# Start shed in another terminal first
TOOL_SHED_API_VERSION=v2 ./run_tool_shed.sh

# Run all functional tests
TOOL_SHED_API_VERSION=v2 uv run pytest tool_shed/test/functional/ -v

# Run specific test
uv run pytest tool_shed/test/functional/test_frontend_login.py -v
```

## Test Categories

### Numbered Tests (`test_0xxx`, `test_1xxx`)

Legacy comprehensive tests using Twill/API:
- `test_0xxx` - Tool Shed functionality (repos, dependencies, metadata)
- `test_1xxx` - Galaxy installation scenarios

These test complex multi-step workflows and dependency chains.

### Named Tests

Modern Playwright/API tests:

| File | Description |
|------|-------------|
| `test_frontend_*.py` | Browser UI tests (Playwright) |
| `test_shed_*.py` | API-level tests |
| `test_repositories_integration.py` | Repository operations |
| `test_component_showcase.py` | Component visual tests |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TOOL_SHED_API_VERSION` | v1 | Set to `v2` for modern API |
| `TOOL_SHED_TEST_BROWSER` | playwright | Browser: `playwright` or `twill` |
| `TOOL_SHED_TEST_EXTERNAL` | - | Use external running shed |
| `TOOL_SHED_TEST_HOST` | localhost | Host for external shed |
| `TOOL_SHED_TEST_SCREENSHOTS` | - | Directory for test screenshots |

## Test Patterns

### API Tests (ShedApiTestCase)

```python
from tool_shed.test.base.twilltestcase import ShedTwillTestCase

class TestMyFeature(ShedTwillTestCase):
    def test_create_repo(self):
        category = self.create_category(name="Test")
        repo = self.get_or_create_repository(
            name="myrepo",
            category=category,
        )
```

### Playwright Tests (PlaywrightTestCase)

```python
from playwright.sync_api import expect
from tool_shed.test.base.playwrighttestcase import PlaywrightTestCase

class TestFrontend(PlaywrightTestCase):
    def test_login(self):
        self.visit_url("/")
        page = self._page
        expect(page.locator(".login-btn")).to_be_visible()
```

### Using Populators

```python
def test_with_populator(self):
    populator = self.populator  # ToolShedPopulator instance
    repo = populator.setup_column_maker_repo()
    populator.upload_revision(repo, "column_maker")
```

## Screenshots

Save screenshots during Playwright tests:

```shell
TOOL_SHED_TEST_SCREENSHOTS=/tmp/screenshots uv run pytest test_frontend_*.py -v
```

## Related Documentation

- [base/README.md](base/README.md) - Test infrastructure
- [test_data/repos/README.md](test_data/repos/README.md) - Mock repository data
