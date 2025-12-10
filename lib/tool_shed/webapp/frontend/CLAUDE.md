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

## Accessibility (WCAG 2.1 AA)

### Key Patterns
- **Skip link**: `App.vue` - hidden until focused, targets `#main-content`
- **Landmarks**: `role="banner"` on header, `role="main"` on page container
- **Live regions**: `ErrorBanner.vue` uses `role="alert"`, `LoadingDiv.vue` uses `role="status"`
- **Icon buttons**: Use `aria-label` not `title` for accessible names
- **Focus indicators**: Global `:focus-visible` styles in `App.vue`

### Components with ARIA
| Component | ARIA Attrs |
|-----------|------------|
| `App.vue` | Skip link, landmarks, focus CSS |
| `ShedToolbar.vue` | `aria-label` on icon buttons, `aria-haspopup` on dropdowns |
| `ErrorBanner.vue` | `role="alert"`, `aria-live="assertive"` |
| `LoadingDiv.vue` | `role="status"`, `aria-live="polite"` |
| `RepositoryExplore.vue` | `aria-label` on FAB and icon buttons |
| `PaginatedRepositoriesGrid.vue` | `aria-label` on table |

### Quasar Notes
- `q-btn-dropdown` auto-manages `aria-expanded`
- `q-select` has built-in label association
- Use `aria-label` on icon-only `q-btn` components
- FABs (`q-fab`) need explicit `aria-label` on trigger

### Notification System
- `util.ts` `notify()` - uses Quasar Notify (toast messages)
- `ErrorBanner.vue` - inline persistent errors with dismiss
- `LoadingDiv.vue` - spinner with status message
