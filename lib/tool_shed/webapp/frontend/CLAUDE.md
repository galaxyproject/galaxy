# Tool Shed 2.0 Frontend

Vue 3 + TypeScript frontend for the Galaxy Tool Shed.

## Stack

- **Framework**: Vue 3 (Composition API + Options API mix)
- **Build**: Vite 4
- **UI**: `@galaxyproject/galaxy-ui` (Galaxy's G-components, from `client/packages/ui`), migrating off Quasar 2 -- see below
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
pnpm dev

# Build
pnpm build

# Typecheck
pnpm typecheck

# Lint
pnpm lint

# Format
pnpm format
```

Backend must be running:

```shell
# From galaxy root
./run_tool_shed.sh
```

For rapid local dev with bootstrapped data:

```shell
TOOL_SHED_CONFIG_OVERRIDE_BOOTSTRAP_ADMIN_API_KEY=tsadminkey \
TOOL_SHED_CONFIG_CONFIG_HG_FOR_DEV=1 \
TOOL_SHED_VITE_PORT=4040 \
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
- `ComponentsShowcase.vue` - Developer page for widget demos

## Component Showcase

When creating reusable UI components, add examples to `src/components/pages/ComponentsShowcase.vue`. This page (accessible via `/showcase`) helps developers see components in isolation. Pattern:

```vue
<component-showcase title="MyComponent">
    <component-showcase-example title="default">
        <my-component />
    </component-showcase-example>
    <component-showcase-example title="with props">
        <my-component some-prop="value" />
    </component-showcase-example>
</component-showcase>
```

When writing unit tests that cover special cases (edge cases, error states, long content, special characters, etc.), consider adding those same cases to the Component Showcase. This helps developers:

- Visually verify the component handles edge cases correctly
- See how the component looks in various states during development
- Document expected behavior for different scenarios

For example, if you test a component with long text or special characters, add showcase examples demonstrating those cases.

## Path Alias

`@/` maps to `src/` directory.

## Accessibility (WCAG 2.1 AA)

### Key Patterns

- **Skip link**: `App.vue` - hidden until focused, targets `#main-content`
- **Landmarks**: `App.vue` renders the page as `<header>` (the masthead) and `<main id="main-content">`
- **Live regions**: `ErrorBanner.vue` uses `role="alert"`, `LoadingDiv.vue` uses `role="status"`
- **Icon buttons**: Use `aria-label` not `title` for accessible names
- **Focus indicators**: Global `:focus-visible` styles in `App.vue`

### Components with ARIA

| Component                       | ARIA Attrs                                                 |
| ------------------------------- | ---------------------------------------------------------- |
| `App.vue`                       | Skip link, landmarks, focus CSS                            |
| `ShedToolbar.vue`               | `aria-label` on icon buttons, `aria-haspopup` on dropdowns |
| `ErrorBanner.vue`               | `role="alert"`, `aria-live="assertive"`                    |
| `LoadingDiv.vue`                | `role="status"`, `aria-live="polite"`                      |
| `ActionMenu.vue`                | `aria-label` on the round toggle, which names its menu     |
| `RepositoryExplore.vue`         | `aria-label` on menu toggle and icon buttons               |
| `RepositoryFileTree.vue`        | `aria-expanded` on folder buttons, `aria-current` on file  |
| `RepositoryContentsPage.vue`    | `<nav aria-label="Files">` around the file tree            |
| `ConfigFileContents.vue`        | `tabindex="0"` on the code block so it scrolls by keyboard |
| `PaginatedRepositoriesGrid.vue` | `aria-label` on table                                      |

### galaxy-ui and the remaining Quasar

New UI uses galaxy-ui components (`GButton`, `GDropdown`, `GAlert`, `GTabs`, `GCollapse`, `GForm*`, ...), FontAwesome 6 icons, and scoped styles on the design tokens (`--color-*`, `--spacing-*`, `--color-galaxy-*`). Quasar now only provides `q-select` (RevisionSelect, SelectUser, OverviewTab) and the Quasar markup inside those selects (RevisionSelect's q-item option rows and badges), which need a galaxy-ui select before they can go.

- The shed is plain Vue 3 (no `@vue/compat`). galaxy-ui's form controls, `GTabs` and `GCollapse` all use `modelValue`, so plain `v-model` works on them. Anything still on Vue 2's `value`/`input` only works in the client, where compat maps it.
- `GDropdown` names its menu from its toggle; icon-only toggles need `aria-label` (see `ActionMenu.vue`).
- Use `aria-label` on icon-only `GButton`s.
- Quasar's own icons (select arrows, table pagination) come from its SVG FontAwesome icon set; there is no icon webfont.

### Notification System

- `util.ts` `notify()` - galaxy-ui toasts (`GToast`, mounted once in `App.vue`)
- `ErrorBanner.vue` - inline persistent errors with dismiss
- `LoadingDiv.vue` - spinner with status message

## Testing (Vitest + Vue Test Utils)

### Setup

Tests use Vitest with `@vue/test-utils` for component testing. Test files should be co-located with components (e.g., `MyComponent.vue` → `MyComponent.test.ts`) or in a `__tests__` directory.

### Best Practices for AI-Developed Tests

#### 1. Test Behavior, Not Implementation

Focus on what the component does from a user's perspective, not internal implementation details:

```typescript
// ✅ Good: Tests user-visible behavior
test("displays error message when API fails", async () => {
    vi.mocked(ToolShedApi).mockReturnValue({ error: { status: 500 } })
    const wrapper = mount(MyComponent)
    await flushPromises()
    expect(wrapper.text()).toContain("Error loading data")
})

// ❌ Bad: Tests implementation details
test("calls fetchData method", () => {
    const fetchDataSpy = vi.spyOn(wrapper.vm, "fetchData")
    // ...
})
```

#### 2. Use Real Queries Over Test IDs

Prefer semantic queries (text, labels, roles) over test IDs:

```typescript
// ✅ Good: Uses accessible queries
const button = wrapper.find('button[aria-label="Submit"]')
const error = wrapper.find('[role="alert"]')

// ❌ Avoid: Test IDs unless necessary
const button = wrapper.find('[data-testid="submit-btn"]')
```

#### 3. Mock External Dependencies

Mock API calls, router, and Pinia stores at the module level:

```typescript
import { vi } from "vitest"
import { ToolShedApi } from "@/schema"

vi.mock("@/schema", () => ({
    ToolShedApi: vi.fn(),
}))

test("loads repository data", async () => {
    vi.mocked(ToolShedApi).mockReturnValue({
        GET: vi.fn().mockResolvedValue({ data: { name: "test-repo" } }),
    })
    // ...
})
```

#### 4. Test Composition API Components Properly

For Composition API components, use `mount()` and interact with the component as a user would:

```typescript
import { mount } from "@vue/test-utils"
import { describe, it, expect, vi, beforeEach } from "vitest"
import MyComponent from "@/components/MyComponent.vue"

describe("MyComponent", () => {
    it("updates count when button clicked", async () => {
        const wrapper = mount(MyComponent)
        const button = wrapper.find("button")
        await button.trigger("click")
        expect(wrapper.text()).toContain("Count: 1")
    })
})
```

#### 5. Test Options API Components

For Options API components, avoid accessing `wrapper.vm` directly. Test through the template:

```typescript
// ✅ Good: Tests through template
test("shows message prop", () => {
    const wrapper = mount(MyComponent, {
        props: { message: "Hello" },
    })
    expect(wrapper.text()).toContain("Hello")
})

// ❌ Avoid: Direct vm access
expect(wrapper.vm.message).toBe("Hello")
```

#### 6. Mock Quasar Components When Needed

Quasar components can be mocked if they're not the focus of the test:

```typescript
import { mount, config } from "@vue/test-utils"

config.global.stubs = {
    "q-btn": { template: "<button><slot /></button>" },
    "q-input": { template: "<input />" },
}
```

#### 7. Test Pinia Stores in Isolation

Test stores separately from components:

```typescript
import { setActivePinia, createPinia } from "pinia"
import { useAuthStore } from "@/stores/auth.store"

describe("auth store", () => {
    beforeEach(() => {
        setActivePinia(createPinia())
    })

    it("sets user on login", () => {
        const store = useAuthStore()
        store.setUser({ id: 1, username: "test" })
        expect(store.user?.username).toBe("test")
    })
})
```

#### 8. Use `flushPromises()` for Async Operations

Wait for async operations to complete:

```typescript
import { flushPromises } from "@vue/test-utils"

test("loads data asynchronously", async () => {
    const wrapper = mount(MyComponent)
    await flushPromises()
    expect(wrapper.text()).toContain("Loaded")
})
```

#### 9. Test Router Navigation

Mock `vue-router` and verify navigation calls:

```typescript
import { vi } from "vitest"
const mockPush = vi.fn()

vi.mock("vue-router", () => ({
    useRouter: () => ({ push: mockPush }),
}))

test("navigates on click", async () => {
    const wrapper = mount(MyComponent)
    await wrapper.find("a").trigger("click")
    expect(mockPush).toHaveBeenCalledWith("/expected-route")
})
```

#### 10. Keep Tests Focused and Independent

Each test should verify one behavior and be independent:

```typescript
// ✅ Good: Focused test
test("displays loading state", () => {
    const wrapper = mount(MyComponent, {
        props: { loading: true },
    })
    expect(wrapper.find('[role="status"]').exists()).toBe(true)
})

// ❌ Bad: Multiple concerns
test("component does everything", () => {
    // Tests loading, error, success, navigation...
})
```

#### 11. Use Descriptive Test Names

Test names should clearly describe what is being tested:

```typescript
// ✅ Good: Clear and descriptive
test("displays error banner when API returns 500", async () => {})
test("hides submit button when form is invalid", () => {})

// ❌ Bad: Vague
test("works correctly", () => {})
test("component test", () => {})
```

#### 12. Clean Up After Tests

Reset mocks and clear state between tests:

```typescript
import { beforeEach, afterEach, vi } from "vitest"

beforeEach(() => {
    vi.clearAllMocks()
})

afterEach(() => {
    vi.restoreAllMocks()
})
```

### Common Patterns

#### Testing Components with Props

```typescript
test("renders with required props", () => {
    const wrapper = mount(MyComponent, {
        props: {
            title: "Test Title",
            count: 5,
        },
    })
    expect(wrapper.text()).toContain("Test Title")
})
```

#### Testing User Interactions

```typescript
test("calls handler on button click", async () => {
    const handleClick = vi.fn()
    const wrapper = mount(MyComponent, {
        props: { onClick: handleClick },
    })
    await wrapper.find("button").trigger("click")
    expect(handleClick).toHaveBeenCalledTimes(1)
})
```

#### Testing Conditional Rendering

```typescript
test("shows content when condition is true", () => {
    const wrapper = mount(MyComponent, {
        props: { show: true },
    })
    expect(wrapper.find(".content").exists()).toBe(true)
})

test("hides content when condition is false", () => {
    const wrapper = mount(MyComponent, {
        props: { show: false },
    })
    expect(wrapper.find(".content").exists()).toBe(false)
})
```

### AI-Specific Guidelines

When generating tests with AI:

1. **Avoid over-testing**: Don't test every method or computed property. Focus on user-facing behavior.
2. **Don't test framework code**: Vue, Quasar, and Pinia are already tested. Test your application logic.
3. **Test edge cases**: Include tests for error states, empty data, and boundary conditions.
4. **Keep tests maintainable**: If implementation changes, tests should only break if behavior changes.
5. **Use TypeScript**: Leverage type safety to catch errors early.
6. **Mock at the right level**: Mock external services (API, router) but test component logic with real data.
