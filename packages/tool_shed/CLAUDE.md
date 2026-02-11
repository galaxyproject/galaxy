# Galaxy Tool Shed

Backend services for the Galaxy Tool Shed.

## Structure
```
tool_shed/
├── managers/         # Business logic (repositories, users, categories)
├── metadata/         # Metadata extraction and management
├── webapp/
│   ├── api/          # Legacy API
│   ├── api2/         # FastAPI v2 endpoints
│   └── frontend/     # Vue 3 frontend (see tool_shed/webapp/frontend/CLAUDE.md)
├── test/             # Tests
│   ├── functional/   # Integration tests (Playwright/Twill)
│   └── test_data/    # Test fixtures
└── util/             # Shared utilities
```

## Running Commands

**IMPORTANT:** Always run commands from the package directory for this
subproject (the directory where this file is located).

Always use `uv run python` and `uv run pytest` to run commands in this directory to ensure the correct environment is used.

Example:
```bash
uv run python -c "from selenium.webdriver.common.by import By; print(By.CLASS_NAME)"
uv run pytest tests/seleniumtests/test_has_driver.py -v
```

**DO NOT run pytest from the monorepo root** (e.g., `../../` from here). This causes fixture scope issues and incorrect test execution. Always run pytest from this directory.

## Testing

Run from this directory (`packages/tool_shed`):

```shell
# Unit tests (no server needed)
uv run pytest tests/tool_shed/

# Functional tests (requires running shed)
TOOL_SHED_API_VERSION=v2 uv run pytest tool_shed/test/functional/test_shed_repositories.py -v
```

### Test Categories

| Type | Location | Server Required | Description |
|------|----------|-----------------|-------------|
| Unit | `tests/tool_shed/` | No | In-memory SQLite, mock app |
| Functional | `tool_shed/test/functional/` | Yes | API + Playwright browser tests |

### Quick Start: Functional Tests

```shell
# Terminal 1: Start shed with v2 API
TOOL_SHED_API_VERSION=v2 ./run_tool_shed.sh

# Terminal 2: Run tests
uv run pytest tool_shed/test/functional/test_frontend_login.py -v
```

### Detailed Documentation

- [tool_shed/test/README.md](tool_shed/test/README.md) - Functional test guide
- [tool_shed/test/base/README.md](tool_shed/test/base/README.md) - Test infrastructure
- [tool_shed/test/test_data/repos/README.md](tool_shed/test/test_data/repos/README.md) - Mock repository data
- [test/unit/tool_shed/README.md](../../test/unit/tool_shed/README.md) - Unit test guide

### Component Showcase & Fixtures

The component showcase (`/_component_showcase`) displays UI components with real API data from generated fixtures. These fixtures are shared between:
- **ComponentsShowcase.vue** - Live demos at `/_component_showcase`
- **Vitest unit tests** - Frontend component tests

```shell
# Regenerate fixtures from real API responses
TOOL_SHED_FIXTURE_OUTPUT_DIR=tool_shed/webapp/frontend/src/components/MetadataInspector/__fixtures__ \
TOOL_SHED_API_VERSION=v2 \
uv run pytest tool_shed/test/functional/test_shed_repositories.py::TestShedRepositoriesApi::test_generate_frontend_fixtures -v

# Format generated files
cd tool_shed/webapp/frontend && npm run format

# Capture component screenshots
TOOL_SHED_TEST_SCREENSHOTS=/tmp/screenshots \
TOOL_SHED_API_VERSION=v2 \
uv run pytest tool_shed/test/functional/test_component_showcase.py -v
```

Regenerate fixtures after: schema changes, API response changes, or metadata bug fixes.

## Running the Tool Shed

```shell
# From galaxy root
TOOL_SHED_API_VERSION=v2 ./run_tool_shed.sh

# With dev conveniences (admin key, hg config, frontend dev server)
TOOL_SHED_CONFIG_OVERRIDE_BOOTSTRAP_ADMIN_API_KEY=tsadminkey \
TOOL_SHED_CONFIG_CONFIG_HG_FOR_DEV=1 \
TOOL_SHED_VITE_PORT=4040 \
TOOL_SHED_API_VERSION=v2 \
./run_tool_shed.sh
```

## API Schema

OpenAPI schema generated from FastAPI endpoints. To regenerate TypeScript types:
```shell
# From galaxy root
make update-client-api-schema
```

Frontend types live in `tool_shed/webapp/frontend/src/schema/schema.ts`.

## Key Managers

- `managers/repositories.py` - Repository CRUD, permissions
- `managers/users.py` - User management
- `managers/categories.py` - Category management
- `metadata/repository_metadata_manager.py` - Metadata extraction/reset

## Frontend

See [tool_shed/webapp/frontend/CLAUDE.md](tool_shed/webapp/frontend/CLAUDE.md) for:
- Vue 3 / Quasar architecture
- Component patterns
- API client usage
- Accessibility guidelines
