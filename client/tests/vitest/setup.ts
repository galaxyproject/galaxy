// Vitest setup file - mirrors Jest setup with Vitest-compatible APIs
import "@testing-library/jest-dom/vitest";
import "fake-indexeddb/auto";
import { vi } from "vitest";
import { configureCompat } from "@vue/compat";

// Vue 3 compat mode configuration
configureCompat({
    MODE: 2,
    GLOBAL_EXTEND: true,
    GLOBAL_MOUNT: true,
    RENDER_FUNCTION: true,
    COMPONENT_FUNCTIONAL: true,
    COMPONENT_V_MODEL: true,
    ATTR_FALSE_VALUE: true,
    ATTR_ENUMERATED_COERCION: true,
    TRANSITION_CLASSES: true,
    FILTERS: true,
    PRIVATE_APIS: true,
});

// Mock hashedUserId and userLocalStorage by default
vi.mock("@/composables/hashedUserId");
vi.mock("@/composables/userLocalStorage");

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

// Import and setup MSW if needed
// This will be uncommented when tests using MSW are migrated
// import { setupServer } from "msw/node";
// export const server = setupServer();
// beforeAll(() => server.listen());
// afterEach(() => server.resetHandlers());
// afterAll(() => server.close());
