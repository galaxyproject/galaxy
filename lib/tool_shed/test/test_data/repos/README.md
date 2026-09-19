# Test Repository Data

This directory contains mock repository data for Tool Shed unit tests. Each subdirectory simulates a Mercurial repository's revision history without requiring actual hg operations.

## Directory Structure

```
repos/
├── column_maker/           # Simple tool with 3 revisions
│   ├── 1/                  # First changeset
│   │   └── column_maker.xml
│   ├── 2/                  # Second changeset
│   │   └── column_maker.xml
│   └── 3/                  # Third changeset
│       └── column_maker.xml
├── data_manager_gaps/      # Data manager with revision gaps
│   ├── 0/
│   ├── 1/
│   └── 2/
└── ...
```

## How It Works

Each numbered subdirectory represents a **changeset/revision** in chronological order:

- `1/` = First revision uploaded to the repository
- `2/` = Second revision (builds on first)
- `3/` = Third revision (builds on second)
- etc.

The contents of each numbered directory are the **complete repository state** at that revision. When uploaded, files are tarred and committed as a new changeset.

### Version Progression Example

In `column_maker/`:
- `1/column_maker.xml` → version="1.1.0", size="40"
- `2/column_maker.xml` → version="1.2.0", size="50"
- `3/column_maker.xml` → version="1.3.0", size="50"

Each revision represents a tool version bump with minor changes.

## Using in Tests

### Primary Function: `upload_directories_to_repository`

Located in `test/unit/tool_shed/_util.py`:

```python
from test.unit.tool_shed._util import upload_directories_to_repository

def test_example(provides_repositories, new_repository):
    # Uploads all revisions (1/, 2/, 3/) sequentially
    upload_directories_to_repository(
        provides_repositories,
        new_repository,
        "column_maker"  # Directory name under repos/
    )

    # Repository now has 3 changesets with metadata
    assert len(new_repository.metadata_revisions) == 3
```

### How Upload Works

1. `repo_tars(test_data_path)` iterates subdirectories in sorted order (1, 2, 3...)
2. Each subdirectory is tarred with the test_data_path as arcname
3. `upload_tar_and_set_metadata()` commits each tar as a new changeset
4. Metadata is generated for each revision

### Fixtures Required

Tests typically use pytest fixtures from `conftest.py`:

```python
@pytest.fixture
def new_repository(provides_repositories):
    """Creates an empty repository for testing."""
    return repository_fixture(
        provides_repositories.app,
        provides_repositories.user,
        random_name()
    )

@pytest.fixture
def provides_repositories(shed_app, default_user):
    """Provides context for repository operations."""
    return provides_repositories_fixture(shed_app, default_user)
```

## Available Test Repositories

| Directory | Description | Revisions |
|-----------|-------------|-----------|
| `column_maker` | Simple tool, version progression | 3 |
| `column_maker_with_download_gaps` | Tool with non-downloadable revisions | 4 |
| `column_maker_with_readme` | Tool with README file | 1 |
| `data_manager_gaps` | Data manager with gaps | 3 |
| `bismark` | Bismark tool | 2 |
| `emboss_5_0470` | EMBOSS tool suite | 2 |
| `package_emboss_5_0_0_0470` | Tool dependency definition | 2 |
| `libx11_proto` | Library dependency | 2 |
| `0480` | Numbered test case | 1 |
| `missing_data_ref` | Missing data reference test | 1 |
| `wrong_data_ref` | Wrong data reference test | 1 |

## Creating New Test Data

1. Create a new directory under `repos/`:
   ```
   repos/my_new_tool/
   ```

2. Add numbered subdirectories for each revision:
   ```
   repos/my_new_tool/1/   # First revision
   repos/my_new_tool/2/   # Second revision
   ```

3. Place repository files in each revision directory:
   ```
   repos/my_new_tool/1/my_tool.xml
   repos/my_new_tool/2/my_tool.xml  # Updated version
   ```

4. Use in tests:
   ```python
   upload_directories_to_repository(provides_repositories, repo, "my_new_tool")
   ```

## Notes

- Subdirectories are processed in **sorted order** (lexicographic), so use numeric names
- Each revision directory should contain the **complete state**, not just diffs
- The `arcname` parameter ensures files are extracted with consistent paths
- Metadata generation happens automatically after each upload
