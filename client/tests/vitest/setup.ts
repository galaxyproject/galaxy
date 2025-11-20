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

// Provide a mocked version of Vue to ensure above settings are not
// overridden by a Vue library that gets imported later
vi.doMock("vue", () => ({
    default: Vue,
    ...Vue,
}));

// Mock window.scrollIntoView (not available in jsdom)
global.scrollIntoView = vi.fn();

// Replace setImmediate with setTimeout to fix certain tests
// @ts-ignore
global.setImmediate = global.setImmediate || ((fn, ...args) => global.setTimeout(fn, 0, ...args));

// Add structuredClone polyfill if not available
if (typeof structuredClone === "undefined") {
    global.structuredClone = (obj: any) => {
        return JSON.parse(JSON.stringify(obj));
    };
}

// Mock IntersectionObserver
class MockIntersectionObserver {
    observe = vi.fn();
    disconnect = vi.fn();
    unobserve = vi.fn();
}

Object.defineProperty(window, "IntersectionObserver", {
    writable: true,
    configurable: true,
    value: MockIntersectionObserver,
});

// Mock HTMLDialogElement methods if not available
if (typeof HTMLDialogElement !== "undefined") {
    HTMLDialogElement.prototype.showModal = HTMLDialogElement.prototype.showModal || vi.fn();
    HTMLDialogElement.prototype.close = HTMLDialogElement.prototype.close || vi.fn();
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

// Import and setup MSW if needed
// This will be uncommented when tests using MSW are migrated
// import { setupServer } from "msw/node";
// export const server = setupServer();
// beforeAll(() => server.listen());
// afterEach(() => server.resetHandlers());
// afterAll(() => server.close());
