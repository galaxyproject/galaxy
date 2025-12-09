# Tool Shed 2.0 Frontend

Vue 3 + TypeScript frontend for the Galaxy Tool Shed.

## Stack
- **Framework**: Vue 3 (Composition API + Options API mix)
- **Build**: Vite 4
- **UI**: Quasar 2
- **State**: Pinia stores
- **API**: openapi-fetch with generated TypeScript types
- **Router**: vue-router 4

## Structure
```
src/
├── api/           # API wrapper functions
├── components/    # Vue components
│   ├── pages/     # Route-level page components
│   └── help/      # Help section components
├── schema/        # OpenAPI-generated types + client
├── stores/        # Pinia stores (auth, categories, repository, users)
├── main.ts        # App entry
├── router.ts      # Vue Router setup
└── routes.ts      # Route definitions
```

## Development

```shell
# Start dev server (port 4040)
yarn dev

# Build
yarn build

# Typecheck
yarn typecheck

# Lint
yarn lint

# Format
yarn format
```

Backend must be running with `TOOL_SHED_API_VERSION=v2`:
```shell
# From galaxy root
TOOL_SHED_API_VERSION=v2 ./run_tool_shed.sh
```

For rapid local dev with bootstrapped data:
```shell
TOOL_SHED_CONFIG_OVERRIDE_BOOTSTRAP_ADMIN_API_KEY=tsadminkey \
TOOL_SHED_CONFIG_CONFIG_HG_FOR_DEV=1 \
TOOL_SHED_VITE_PORT=4040 \
TOOL_SHED_API_VERSION=v2 \
./run_tool_shed.sh
```

## API Pattern
API calls use openapi-fetch typed client via `ToolShedApi()` in `src/schema/client.ts`:
```typescript
import { ToolShedApi } from "@/schema"
const { data } = await ToolShedApi().GET("/api/repositories", { params: { query: params } })
```

## Key Components
- `ShedToolbar.vue` - Main navigation toolbar
- `RepositoryPage.vue` - Single repository view
- `LandingPage.vue` - Homepage
- `PaginatedRepositoriesGrid.vue` - Repository listing grid

## Path Alias
`@/` maps to `src/` directory.
