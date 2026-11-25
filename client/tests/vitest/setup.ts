// Vitest setup file - mirrors Jest setup with Vitest-compatible APIs
import "@testing-library/jest-dom/vitest";
import "fake-indexeddb/auto";
import "vitest-location-mock";

import { config } from "@vue/test-utils";
import { vi } from "vitest";
import type { ComponentPublicInstance } from "vue";

import { GLOBAL_COMPAT_CONFIG } from "@/compat-config";
import { vNoSanitizeHtml } from "@/directives/vNoSanitizeHtml";
import { LEGACY_COMPAT_CONFIG } from "@/legacy-libraries";

// Straight from the file: the galaxy-ui index would load every component here,
// before test files can mock their dependencies (@floating-ui/dom).
import { vSanitizeHtml } from "../../packages/ui/src/directives/vSanitizeHtml";

// Mock g-tooltip directive globally so components don't trigger
// "Failed to resolve directive" warnings during tests.
config.global.directives = {
    ...(config.global.directives ?? {}),
    "g-tooltip": {
        mounted(el: HTMLElement, binding: { value?: string }) {
            el.setAttribute("data-mock-directive", binding.value || el.title || "");
        },
    },
    // v-sanitize-html is the real directive; only the DOMPurify call behind it is
    // replaced with a pass-through spy (see galaxy-ui's directives/__mocks__/sanitizeHtml.ts).
    "sanitize-html": vSanitizeHtml,
    "no-sanitize-html": vNoSanitizeHtml,
};
vi.mock("../../packages/ui/src/directives/sanitizeHtml");

// Mock hashedUserId and userLocalStorage by default
vi.mock("@/composables/hashedUserId");
vi.mock("@/composables/userLocalStorage");

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

// Vue warns once per component and deprecation when compat keeps a Vue 2
// behavior on. That happens only where it's on by choice: in the Vue 2 library
// components (LEGACY_COMPAT_CONFIG) and for the flags compat-config.js turns on
// globally. Galaxy code hitting a Vue 2 behavior that is off gets the Vue 3
// behavior or an error, never one of these warnings; an error still fails the test.
const ENABLED_COMPAT_DEPRECATIONS = new Set(
    [...Object.entries(LEGACY_COMPAT_CONFIG), ...Object.entries(GLOBAL_COMPAT_CONFIG)]
        .filter(([, value]) => value === true)
        .map(([flag]) => flag),
);
// Compat reads this global flag without looking at the component, so Galaxy
// components get Vue 2's deep data merge too. Let its warning through only when
// the component merging its data is a Vue 2 library one.
const LIBRARY_ONLY_DEPRECATIONS = new Set(["OPTIONS_DATA_MERGE"]);
const COMPAT_DEPRECATION = /^(?:\[Vue warn\]: )?\(deprecation ([A-Z_]+)\)/;

function compatDeprecationFlag(message: string) {
    return COMPAT_DEPRECATION.exec(message)?.[1];
}

function isLibraryComponent(instance: ComponentPublicInstance | null) {
    return (instance?.$.type as { compatConfig?: unknown } | undefined)?.compatConfig === LEGACY_COMPAT_CONFIG;
}

// Vue passes a warning's component props to console.warn as raw objects, and
// vitest-fail-on-console formats every argument before deciding whether to
// silence it -- a big enough props object overflows the string it builds.
// Hand Vue's warnings to the console as the plain strings Vue already has.
config.global.config.warnHandler = (message: string, instance, trace: string) => {
    const flag = compatDeprecationFlag(message);
    if (flag && LIBRARY_ONLY_DEPRECATIONS.has(flag) && isLibraryComponent(instance)) {
        return;
    }
    console.warn(`[Vue warn]: ${message}${trace ? `\n${trace}` : ""}`);
};

function isEnabledCompatDeprecation(message: string) {
    const flag = compatDeprecationFlag(message);
    return flag !== undefined && ENABLED_COMPAT_DEPRECATIONS.has(flag) && !LIBRARY_ONLY_DEPRECATIONS.has(flag);
}

// A test-utils stub renders the stubbed component's props on its <x-stub>
// element, and Vue sets a prop as a DOM property when the element has one of
// that name. For read-only ones (`prefix`, `attributes`) the assignment fails.
// Only the stub's own element is involved, never a real component's.
const STUB_DOM_PROP = /^\[Vue warn\]: Failed setting prop "[^"]+" on <[a-z0-9-]+-stub>/;

// Fail tests that log console errors or warnings, except for the messages
// silenceMessage lets through. Anything else, including every other Vue or
// Vue Router warning, fails the test that logged it.
const failOnConsole = (await import("vitest-fail-on-console")).default;
failOnConsole({
    shouldFailOnError: true,
    shouldFailOnWarn: true,
    silenceMessage: (message: string, methodName: string) => {
        return methodName === "warn" && (isEnabledCompatDeprecation(message) || STUB_DOM_PROP.test(message));
    },
});

// Import and setup MSW if needed
// This will be uncommented when tests using MSW are migrated
// import { setupServer } from "msw/node";
// export const server = setupServer();
// beforeAll(() => server.listen());
// afterEach(() => server.resetHandlers());
// afterAll(() => server.close());
