# Tool Shed Unit Tests

Fast unit tests using in-memory SQLite and mock app. No running server required.

## Running Tests

```shell
# From packages/tool_shed directory
uv run pytest tests/tool_shed/ -v

# Specific test
uv run pytest tests/tool_shed/test_repository_metadata_manager.py -v
```

Note: `tests/tool_shed/` is a symlink to `test/unit/tool_shed/`.

## Test Files

| File | Tests |
|------|-------|
| `test_repository_metadata_manager.py` | Metadata reset, dry run |
| `test_pagination.py` | Pagination utilities |
| `test_tool_panel_manager.py` | Tool panel operations |
| `test_hg_util.py` | Mercurial utilities |
| `test_tool_validation.py` | Tool XML validation |
| `test_repository_utils.py` | Repository utilities |
| `test_shed_index.py` | Search indexing |
| `test_dbscript.py` | Database migrations |
| `test_model_cache.py` | Model caching |
| `test_tool_source.py` | Tool source parsing |
| `test_trs_tool.py` | TRS tool handling |

## Fixtures

Defined in `conftest.py`:

### `shed_app`

Mock Tool Shed application with in-memory SQLite:

```python
def test_example(shed_app):
    # shed_app is a TestToolShedApp instance
    assert shed_app.model is not None
```

### `new_user`

Creates a random test user:

```python
def test_with_user(new_user):
    assert new_user.username
    assert new_user.email
```

### `new_repository`

Creates an empty repository:

```python
def test_repo(new_repository):
    assert new_repository.name
    assert len(new_repository.downloadable_revisions) == 0
```

### `provides_repositories`

Context for repository operations:

```python
def test_upload(provides_repositories, new_repository):
    upload_directories_to_repository(
        provides_repositories,
        new_repository,
        "column_maker"  # From test_data/repos/
    )
    assert len(new_repository.downloadable_revisions) == 3
```

## Utilities

Located in `_util.py`:

### TestToolShedApp

Mock application for unit tests:

```python
from ._util import TestToolShedApp

app = TestToolShedApp()
# Uses in-memory SQLite
# Has mock hgweb config
# Has security/encoding helpers
```

### upload_directories_to_repository

Upload test data to a repository:

```python
from ._util import upload_directories_to_repository

upload_directories_to_repository(
    provides_repositories,
    repository,
    "column_maker"  # Directory name under test_data/repos/
)
# Uploads all revisions (1/, 2/, 3/) as separate changesets
```

### Other Utilities

```python
from ._util import (
    user_fixture,        # Create test user
    repository_fixture,  # Create test repository
    random_name,         # Generate random name
    create_category,     # Create category
    attach_category,     # Associate repo with category
)
```

## Test Data

Mock repository data in `tool_shed/test/test_data/repos/`.

See [repos/README.md](../../packages/tool_shed/tool_shed/test/test_data/repos/README.md) for:
- Directory structure (numbered revisions)
- Available test repositories
- Creating new test data

## Example Test

```python
from tool_shed.context import ProvidesRepositoriesContext
from tool_shed.metadata import repository_metadata_manager
from tool_shed.webapp.model import Repository
from ._util import upload_directories_to_repository


def test_reset_metadata(
    provides_repositories: ProvidesRepositoriesContext,
    new_repository: Repository
):
    # Upload test data
    upload_directories_to_repository(
        provides_repositories,
        new_repository,
        "column_maker"
    )
    assert len(new_repository.downloadable_revisions) == 3

    # Test metadata reset
    rmm = repository_metadata_manager.RepositoryMetadataManager(
        provides_repositories,
        repository=new_repository,
        resetting_all_metadata_on_repository=True,
        updating_installed_repository=False,
        persist=False,
    )
    repo_path = new_repository.repo_path(app=provides_repositories.app)
    rmm.reset_all_metadata_on_repository_in_tool_shed(
        repository_clone_url=repo_path
    )
    assert len(new_repository.downloadable_revisions) == 3
```
