// Vitest setup file - mirrors Jest setup with Vitest-compatible APIs
import "@testing-library/jest-dom/vitest";
import "fake-indexeddb/auto";
import "vitest-location-mock";

import { configureCompat } from "@vue/compat";
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

// Fail tests that log console errors or warnings
// Replaces jest-fail-on-console functionality
const failOnConsole = (await import("vitest-fail-on-console")).default;
failOnConsole({
    shouldFailOnError: true,
    shouldFailOnWarn: (message: string) => {
        // Don't fail on Vue compat mode warnings during migration (but still show them)
        if (message.includes("[Vue warn]")) {
            return false;
        }
        // Don't fail on Bootstrap-Vue registration warnings
        if (message.includes("has already been registered")) {
            return false;
        }
        // Fail on other warnings
        return true;
    },
});

// Import and setup MSW if needed
// This will be uncommented when tests using MSW are migrated
// import { setupServer } from "msw/node";
// export const server = setupServer();
// beforeAll(() => server.listen());
// afterEach(() => server.resetHandlers());
// afterAll(() => server.close());
