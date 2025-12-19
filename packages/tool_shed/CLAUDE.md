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
# Unit tests
uv run pytest tool_shed/test/

# Specific test file
uv run pytest tool_shed/test/functional/test_frontend_login.py -v
```

### Playwright Tests

Playwright tests require a running tool shed with v2 API. In one terminal:
```shell
# From galaxy root
TOOL_SHED_API_VERSION=v2 ./run_tool_shed.sh
```

Then run tests:
```shell
uv run pytest tool_shed/test/functional/test_frontend_login.py -v
```

### Frontend Build

Before running Playwright tests, build the frontend:
```shell
cd tool_shed/webapp/frontend
npm install --legacy-peer-deps
npm run build
```

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
