// Vitest setup file - mirrors Jest setup with Vitest-compatible APIs
import "@testing-library/jest-dom/vitest";
import "fake-indexeddb/auto";
import "vitest-location-mock";

import { vi } from "vitest";
// Vue configuration
import Vue from "vue";

Vue.config.productionTip = false;
Vue.config.devtools = false;

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

// Provide a mocked version of Vue to ensure above settings are not
// overridden by a Vue library that gets imported later
vi.doMock("vue", () => ({
    default: Vue,
    ...Vue,
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
    shouldFailOnWarn: true,
});

// Import and setup MSW if needed
// This will be uncommented when tests using MSW are migrated
// import { setupServer } from "msw/node";
// export const server = setupServer();
// beforeAll(() => server.listen());
// afterEach(() => server.resetHandlers());
// afterAll(() => server.close());
