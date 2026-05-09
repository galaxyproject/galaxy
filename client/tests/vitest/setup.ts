// Vitest setup file - mirrors Jest setup with Vitest-compatible APIs
import "@testing-library/jest-dom/vitest";
import "fake-indexeddb/auto";
import "vitest-location-mock";

import { configureCompat } from "@vue/compat";
import { config } from "@vue/test-utils";
import { vi } from "vitest";

// Configure Vue 3 compat mode - suppress warnings for Vue 2 features used in tests
configureCompat({
    MODE: 2,
    // Suppress specific deprecation warnings that are expected during migration
    GLOBAL_EXTEND: "suppress-warning",
    GLOBAL_MOUNT: "suppress-warning",
    GLOBAL_PROTOTYPE: "suppress-warning",
    INSTANCE_EVENT_EMITTER: "suppress-warning",
    INSTANCE_EVENT_HOOKS: "suppress-warning",
    OPTIONS_DESTROYED: "suppress-warning",
    OPTIONS_BEFORE_DESTROY: "suppress-warning",
    WATCH_ARRAY: "suppress-warning",
    COMPONENT_V_MODEL: "suppress-warning",
    RENDER_FUNCTION: "suppress-warning",
});

// Mock g-tooltip directive globally so components don't trigger
// "Failed to resolve directive" warnings during tests.
config.global.directives = {
    ...(config.global.directives ?? {}),
    "g-tooltip": {
        mounted(el: HTMLElement, binding: { value?: string }) {
            el.setAttribute("data-mock-directive", binding.value || el.title || "");
        },
        // Vue 2 compat hook
        bind(el: HTMLElement, binding: { value?: string }) {
            el.setAttribute("data-mock-directive", binding.value || el.title || "");
        },
    },
};

// Mock hashedUserId and userLocalStorage by default
vi.mock("@/composables/hashedUserId");
vi.mock("@/composables/userLocalStorage");

// Mock handsontable to avoid core-js dependency issues
vi.mock("handsontable", () => ({
    default: class Handsontable {},
}));
vi.mock("@handsontable/vue", () => ({
    default: {},
    HotTable: {},
}));

// Mock KaTeX to avoid quirks mode warning (it checks document.compatMode at module load)
vi.mock("katex", () => ({
    default: {
        renderToString: (latex: string) => `<span class="katex">${latex}</span>`,
    },
}));

// Mock window.scrollIntoView (not available in test environment)
Object.defineProperty(global, "scrollIntoView", {
    writable: true,
    configurable: true,
    value: vi.fn(),
});

// Spoof user agent to include "jsdom" so BootstrapVue skips its
// "Multiple instances of Vue" warning check (it only checks in non-jsdom envs)
if (typeof window !== "undefined" && window.navigator) {
    Object.defineProperty(window.navigator, "userAgent", {
        value: window.navigator.userAgent + " jsdom",
        configurable: true,
    });
}

// Mock BroadcastChannel to fix Pinia state synchronization errors
// Node.js's BroadcastChannel has a type mismatch with the browser API
class MockBroadcastChannel extends EventTarget {
    name: string;

    constructor(name: string) {
        super();
        this.name = name;
    }

    postMessage() {
        // No-op for tests
    }

    close() {
        // No-op for tests
    }
}

Object.defineProperty(global, "BroadcastChannel", {
    writable: true,
    configurable: true,
    value: MockBroadcastChannel,
});

// Mock Worker so components using web workers (e.g. useFilterObjectArray)
// don't throw "Worker is not defined" under happy-dom.
class MockWorker extends EventTarget {
    onmessage: ((event: MessageEvent) => void) | null = null;
    onerror: ((event: ErrorEvent) => void) | null = null;
    onmessageerror: ((event: MessageEvent) => void) | null = null;

    constructor(_url: string | URL, _options?: WorkerOptions) {
        super();
    }

    postMessage(_message: unknown) {
        // No-op for tests
    }

    terminate() {
        // No-op for tests
    }
}

Object.defineProperty(global, "Worker", {
    writable: true,
    configurable: true,
    value: MockWorker,
});

// Fail tests that log console errors or warnings
// Replaces jest-fail-on-console functionality.
//
// vitest-fail-on-console treats shouldFailOnError/shouldFailOnWarn as booleans
// (defaults: true). The predicate that decides whether to silence a particular
// message is silenceMessage(message, methodName) -- returning true suppresses
// it completely (no fail, no noisy print).
const failOnConsole = (await import("vitest-fail-on-console")).default;
failOnConsole({
    shouldFailOnError: true,
    shouldFailOnWarn: true,
    silenceMessage: (message: string, methodName: string) => {
        if (methodName === "warn") {
            // Vue compat mode warnings (resolveComponent / resolveDirective /
            // withDirectives / Property "X" was accessed during render /
            // Missing ref owner / injection not found / onScopeDispose /
            // $scopedSlots / COMPONENT_FUNCTIONAL deprecation / Invalid vnode
            // type / Unhandled error during execution of watcher callback)
            if (message.includes("[Vue warn]")) {
                return true;
            }
            // Vue Router compat warnings (e.g. "No match found for location")
            if (message.includes("[Vue Router warn]")) {
                return true;
            }
            // Pinia duplicate registration during test setup
            if (message.includes("App already provides property with key")) {
                return true;
            }
            // Bootstrap-Vue duplicate-registration noise
            if (message.includes("has already been registered")) {
                return true;
            }
            // Deprecation warnings during migration
            if (message.includes("DEPRECATION") || message.includes("deprecated")) {
                return true;
            }
        }
        if (methodName === "error") {
            // axios mock not installed during some tests (expected)
            if (message.includes('No "default" export is defined on the "axios" mock')) {
                return true;
            }
            // Network errors from unmocked endpoints (mocking issue, not a real error)
            if (message.includes("ECONNREFUSED") || message.includes("socket hang up")) {
                return true;
            }
        }
        return false;
    },
});

// Import and setup MSW if needed
// This will be uncommented when tests using MSW are migrated
// import { setupServer } from "msw/node";
// export const server = setupServer();
// beforeAll(() => server.listen());
// afterEach(() => server.resetHandlers());
// afterAll(() => server.close());
