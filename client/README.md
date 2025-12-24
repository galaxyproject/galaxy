# Client Build System

Installs, stages, and builds the client-side scripts necessary for running the
Galaxy web client. When started through `run.sh` or any other method that
utilizes `scripts/common_startup.sh`, Galaxy will (since 18.09) _automatically_
build the client as a part of server startup when it detects changes unless that
functionality is explicitly disabled.

The base dependencies used are Node.js and pnpm. Galaxy includes appropriate
versions of these in the virtual environment, and they can be accessed by
activating that with `. .venv/bin/activate` from the Galaxy root directory.

If you'd like to install your dependencies external to Galaxy, on OSX the
easiest way to get set up is using `homebrew` and the command `brew install
node pnpm`. More information, including instructions for other platforms, is
available at [https://nodejs.org](https://nodejs.org) and
[https://pnpm.io/](https://pnpm.io/).

The Galaxy client build has necessarily grown more complex in the past several
years, but we are still trying to keep things as simple as possible for
everyone. If you're having any trouble with building the client after following
the instructions below, please create an issue on GitHub or reach out for help
directly on Gitter at
[https://gitter.im/galaxyproject/Lobby](https://gitter.im/galaxyproject/Lobby).

## Complete Client Build

There are many moving parts to the client build system, but the entry point for
most people is the 'client' rule in the Makefile at the root of the Galaxy
repository. Execute the following to perform a complete build suitable for local
development, including dependency staging, style building, script processing,
and bundling. This is a development-specific build that includes extra debugging
features and excludes several production optimizations made during the build
process.

    make client

For a production build, suitable for deploying to a live server, use the
following:

    make client-production

And, lastly, if you want a production build that includes sourcemaps to allow
for inspection of live javascript to facilitate debugging, use:

    make client-production-maps

Important Note: The Galaxy repository does not include client script artifacts,
and these should not be committed.

## Automatic Rebuilding

When you're actively developing, it is convenient to have the client
automatically rebuild every time you save a file. You can do this using:

    make client-dev-server

Or, with the package scripts from this `client` directory:

    pnpm run develop

This will start up an extra client development server running on port 5173. Open
your browser to `http://localhost:5173` (instead of the default 8080 that Galaxy
would run on), and you should see Galaxy like normal. Except now, when you
change client code it'll automatically rebuild _and_ reload the relevant portion
of the application for you. Lastly, if you are running Galaxy at a location
other than the default, you can specify a different proxy target (in this
example, port 8000) using the GALAXY_URL environment variable:

    GALAXY_URL="http://localhost:8000" make client-dev-server

Sometimes you want to run your local UI against a remote Galaxy server. This is
also possible if you set the `CHANGE_ORIGIN` environment variable:

    CHANGE_ORIGIN=true GALAXY_URL="https://usegalaxy.org/" make client-dev-server

You can also specify a particular port to bind the dev server to:

    VITE_PORT=8083 pnpm run develop

## Running a Separate Server

When developing the client it can be helpful to run a local server for the
client to connect to, and run the client separately with one of the above
commands. This command will run galaxy without building the client:

    make skip-client

Or by setting the following environment variable and running Galaxy however you
prefer:

    GALAXY_SKIP_CLIENT_BUILD=1 ./run.sh

## Changing Styles/CSS

Galaxy uses Sass for globally applied styling, which is a superset of CSS that
compiles down to regular CSS. Most Galaxy styling source (.scss) files are kept
in `client/src/style/scss`. Many components will also have local style blocks
containing styles that are particular to that individual component and do not
apply site-wide.

On build, the compiled css bundle is served at `/static/dist/base.css`.

As mentioned above, `make client` will rebuild styles as a part of the build
process. For iterative development, "Watch Mode" rebuilds as described above do
include style changes.

## Client-Side Unit Testing

Galaxy's client is undergoing an extensive refactoring and modernizing process.
As part of this initiative, we would like to request that all new client-side
code submissions come with accompanying javascript unit-tests for the
developer-facing API of your new code.

### Testing Technologies

[Galaxy uses Vitest](https://vitest.dev/) for its client-side unit testing
framework.

For testing Vue components, we use the [Vue testing
utils](https://vue-test-utils.vuejs.org/) to mount individual components in a
test bed and check them for rendered features. Please use Vitest's mocking
capabilities for isolating test functionality.

### Linting

We use [Prettier](https://prettier.io/) to enforce code style and best
practices. Before submitting a pull request, run the following commands
as appropriate to ensure all the code is properly formatted:

    make client-lint
    make client-format

### Running the tests

#### At Build-Time

To simply run all the javascript unit tests, you can use make from the root
directory. This is what happens during a complete client build.

     make client-test

#### During Development

During client-side development, it is more convenient to have granular testing
options. The various testing scripts are defined inside package.json within the
client folder and are called with `pnpm` as demonstrated in the following
commands.

This is what CI is going to run, and also what 'make client-test' invokes,
executing all the client tests:

     pnpm test

##### Watch and rerun unit tests every time a source file changes

This is incredibly handy, and there are a host of options in the interactive
terminal this starts for executing Vitest tests.

     pnpm test:watch

##### Run only specified test files when a source file changes

    pnpm test:watch MyModule

    pnpm test:watch Dialog

    pnpm test:watch workflow/run

### Testing Best Practices and Patterns

#### Test File Structure

Test files should be placed adjacent to the code they test with a `.test.ts` or `.test.js` extension:

```
src/components/MyComponent/
├── MyComponent.vue
├── MyComponent.test.ts
└── test-utils.ts        # optional: shared test utilities
```

Standard imports pattern:

```typescript
import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import MyComponent from "./MyComponent.vue";
```

#### Galaxy Testing Infrastructure

**LocalVue Setup**: Use the shared `getLocalVue()` helper which configures BootstrapVue, Pinia, localization, and common directives:

```typescript
const localVue = getLocalVue();
// or with localization instrumentation for testing l() calls:
const localVue = getLocalVue(true);
```

**Test Data Factories**: Use factory functions for consistent test data:

```typescript
import { getFakeRegisteredUser } from "@tests/test-data";

const user = getFakeRegisteredUser({ id: "custom-id", is_admin: true });
```

Create domain-specific factories for complex test data:

```typescript
// In test-utils.ts or inline
function createFakeHistory(overrides = {}) {
    return {
        id: "history-id",
        name: "Test History",
        deleted: false,
        ...overrides,
    };
}
```

**Suppressing Warnings**: Use helpers to suppress known console warnings:

```typescript
import { suppressBootstrapVueWarnings, suppressLucideVue2Deprecation } from "@tests/vitest/helpers";

beforeEach(() => {
    suppressBootstrapVueWarnings();
    suppressLucideVue2Deprecation();
});
```

#### API Mocking with MSW

Galaxy uses [Mock Service Worker (MSW)](https://mswjs.io/) with
[OpenAPI-MSW](https://github.com/christoph-fricke/openapi-msw) for type-safe API mocking.
This is the preferred approach over axios-mock-adapter:

```typescript
import { useServerMock } from "@/api/client/__mocks__";

const { server, http } = useServerMock();

beforeEach(() => {
    server.use(
        http.get("/api/histories/{history_id}", ({ response }) => {
            return response(200).json({
                id: "history-id",
                name: "Test History",
            });
        }),
        http.post("/api/jobs", ({ response }) => {
            return response(201).json({ id: "job-id" });
        }),
    );
});
```

For untyped responses (endpoints not in OpenAPI spec):

```typescript
import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

server.use(
    http.get("/api/configuration", ({ response }) => {
        return response.untyped(HttpResponse.json({ enable_feature: true }));
    }),
);
```

See the [MSW documentation](https://mswjs.io/docs/) for advanced usage patterns.

#### Mount vs ShallowMount

Vue Test Utils provides two mounting functions: `mount` and `shallowMount`. In Galaxy, **prefer `shallowMount`** for client unit tests.

**`shallowMount`** (preferred):

- Renders the component but stubs all child components
- Tests the component in isolation
- Faster execution, fewer dependencies to mock
- Avoids cascading API calls from child components

**`mount`**:

- Renders the full component tree including all children
- Tests component integration with children
- Slower, requires more mocking setup

```typescript
import { shallowMount, mount } from "@vue/test-utils";

// Preferred: isolated unit test
const wrapper = shallowMount(MyComponent, { localVue, pinia });

// Use sparingly: when testing parent-child interaction
const wrapper = mount(MyComponent, { localVue, pinia });
```

**Why shallowMount for Galaxy?** Client-side tests should be focused unit tests that verify individual component behavior. Integration testing across multiple components is better handled by Galaxy's Selenium/Playwright test framework, which tests the full application stack in a real browser environment. This separation keeps unit tests fast, focused, and maintainable.

See [Vue Test Utils: Stubs and Shallow Mount](https://test-utils.vuejs.org/guide/advanced/stubs-shallow-mount) for more details.

#### Component Testing Patterns

**Mount Wrapper Factories**: Create reusable mount functions for complex component setup:

```typescript
async function mountMyComponent(propsData = {}, options = {}) {
    const pinia = createTestingPinia({ createSpy: vi.fn });

    const wrapper = shallowMount(MyComponent, {
        localVue,
        propsData: {
            defaultProp: "value",
            ...propsData,
        },
        pinia,
        ...options,
    });

    await flushPromises();
    return wrapper;
}
```

**Selector Constants**: Define selectors as constants for maintainability:

```typescript
const SELECTORS = {
    SUBMIT_BUTTON: "[data-description='submit button']",
    ERROR_MESSAGE: "[data-description='error message']",
    USER_NAME: "#user-name-input",
};

it("shows error on failure", async () => {
    const wrapper = await mountMyComponent();
    expect(wrapper.find(SELECTORS.ERROR_MESSAGE).exists()).toBe(true);
});
```

**Testing Emitted Events**:

```typescript
it("emits update on change", async () => {
    const wrapper = await mountMyComponent();
    await wrapper.find("input").setValue("new value");

    expect(wrapper.emitted()["update:value"]).toBeTruthy();
    expect(wrapper.emitted()["update:value"][0][0]).toBe("new value");
});
```

#### Pinia Store Testing

**Setup for Component Tests**:

```typescript
import { createTestingPinia } from "@pinia/testing";
import { setActivePinia } from "pinia";

const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
setActivePinia(pinia);

const wrapper = shallowMount(MyComponent, { localVue, pinia });

// Access and manipulate stores
const userStore = useUserStore();
userStore.currentUser = getFakeRegisteredUser();
```

**Isolated Store Tests**:

```typescript
import { createPinia, setActivePinia } from "pinia";

describe("useMyStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    it("updates state correctly", () => {
        const store = useMyStore();
        store.doAction();
        expect(store.someState).toBe("expected");
    });
});
```

#### Composable Testing

Test composables by mounting a minimal component that uses them:

```typescript
import { mount } from "@vue/test-utils";
import { ref } from "vue";

import { useMyComposable } from "./useMyComposable";

function createTestComponent(initialValue) {
    return mount({
        template: "<div></div>",
        setup() {
            const input = ref(initialValue);
            const { result, doSomething } = useMyComposable(input);
            return { result, doSomething };
        },
    });
}

it("computes result correctly", () => {
    const wrapper = createTestComponent("input");
    expect(wrapper.vm.result).toBe("expected");
});
```

#### Mocking Modules and Composables

Mock at file level before imports are resolved:

```typescript
vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({
        config: { enable_feature: true },
        isConfigLoaded: true,
    })),
}));

vi.mock("vue-router/composables", () => ({
    useRoute: vi.fn(() => ({ params: { id: "123" } })),
}));
```

#### Async Operations

Always use `flushPromises()` after operations that trigger API calls or state updates:

```typescript
import flushPromises from "flush-promises";

it("loads data on mount", async () => {
    const wrapper = shallowMount(MyComponent, { localVue, pinia });
    await flushPromises(); // Wait for mounted() API calls

    expect(wrapper.find(".data").exists()).toBe(true);
});
```

For Vue reactivity, use `nextTick()`:

```typescript
import { nextTick } from "vue";

await wrapper.setProps({ value: "new" });
await nextTick();
expect(wrapper.text()).toContain("new");
```

#### Useful Test Pattern Examples

The following test files demonstrate specific patterns well and can serve as references:

| Pattern                       | Example File                                                            | What It Demonstrates                                                                  |
| ----------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| **API mocking basics**        | `src/api/client/serverMock.test.ts`                                     | Core useServerMock patterns: query params, path params, status codes, typed responses |
| **Multiple HTTP methods**     | `src/composables/userToolCredentials.test.ts`                           | GET, POST, PUT, DELETE in one test; query param filtering; 204 empty responses        |
| **Conditional API responses** | `src/composables/taskMonitor.test.ts`                                   | Switch statement pattern for different task states (PENDING, SUCCESS, FAILURE)        |
| **Paginated API responses**   | `src/stores/collectionElementsStore.test.ts`                            | Dynamic response generation based on offset/limit query params                        |
| **API error handling**        | `src/components/History/Export/HistoryExport.test.ts`                   | 4XX/5XX error responses with err_code and err_msg                                     |
| **Config composable mock**    | `src/entry/analysis/modules/Login.test.ts`                              | Using setMockConfig() helper to customize Galaxy configuration                        |
| **Config mock (simple)**      | `src/components/Citation/CitationsList.test.ts`                         | Basic vi.mock pattern for useConfig                                                   |
| **Shared YAML**               | `src/components/Collections/pairing.test.ts`                            | Defining YAML specifications that can be shared between frontend and backend          |
| **Stub with methods**         | `src/components/Workflow/Editor/Index.test.ts`                          | Stubbing components with methods and `expose` for template refs                       |
| **Stub with factory**         | `src/components/Tool/ToolForm.test.js`                                  | MockCurrentHistory() factory for configurable stubs                                   |
| **Selective stubbing**        | `src/components/History/Content/ContentItem.test.js`                    | Mix of stubbed (`true`) and rendered (`false`) components                             |
| **Named slots**               | `src/components/Popper/Popper.test.js`                                  | Testing multiple named slots with HTML string content                                 |
| **Multiple slots**            | `src/components/Form/FormCardSticky.test.js`                            | Testing buttons, default, and footer slots together                                   |
| **Scoped slots mock**         | `src/components/Visualizations/DisplayApplications.test.js`             | Mocking provider component with $scopedSlots                                          |
| **Slots in stubs**            | `src/components/Markdown/Editor/Configurations/ConfigureHeader.test.js` | Stub templates that include slot definitions                                          |
| **Test data factory**         | `tests/test-data/index.ts`                                              | getFakeRegisteredUser() pattern for reusable mock data                                |

#### Best Practices Summary

1. **Test behavior, not implementation**: Focus on what users see, not internal methods
2. **Avoid accessing `wrapper.vm` directly**: Test through the template when possible
3. **Keep tests focused**: One behavior per test
4. **Use descriptive names**: `"displays error banner when API returns 500"` not `"test error"`
5. **Clean up between tests**: Reset mocks in `beforeEach`/`afterEach`
6. **Mock at appropriate level**: Mock external services, test component logic with real data
7. **Don't test framework code**: Vue and Pinia are already tested
8. **Test edge cases**: Error states, empty data, boundary conditions
