/**
 * Unit test debugging utilities for Vitest
 *
 * Note: For Vue 3 / Vue Test Utils v2, we no longer use createLocalVue.
 * Instead, plugins are passed via the `global` mount option.
 */
import { expect, vi } from "vitest";
import { createRouter, createWebHistory } from "vue-router";

import { localizationPlugin } from "@/components/plugins/localization";
import _l from "@/utils/localization";

function testLocalize(text) {
    if (text) {
        return `test_localized<${text}>`;
    } else {
        return text;
    }
}

// Mocked directive for tooltips/popovers
const mockedDirective = {
    mounted(el, binding) {
        el.setAttribute("data-mock-directive", binding.value || el.title);
    },
    // Vue 2 compat hook
    bind(el, binding) {
        el.setAttribute("data-mock-directive", binding.value || el.title);
    },
};

/**
 * Returns the global mount configuration for Vue Test Utils v2.
 * Use this with mount() like: mount(Component, { global: getLocalVue() })
 *
 * Note: BootstrapVue and vue-rx are not compatible with Vue 3.
 * Use component-specific stubs for bootstrap components in tests.
 */
export function getLocalVue(instrumentLocalization = false) {
    const l = instrumentLocalization ? testLocalize : _l;

    return {
        plugins: [[localizationPlugin, l]],
        directives: {
            "b-tooltip": mockedDirective,
            "b-popover": mockedDirective,
        },
        stubs: {
            // Stub common bootstrap-vue components
            "b-button": true,
            "b-form-input": true,
            "b-form-checkbox": true,
            "b-modal": true,
            "b-card": true,
            "b-dropdown": true,
            "b-dropdown-item": true,
            "b-alert": true,
            "b-badge": true,
            "b-spinner": true,
            "b-link": true,
            "b-collapse": true,
            "b-form-group": true,
            "b-form-select": true,
            "b-form-textarea": true,
            "b-table": true,
            "b-pagination": true,
            "b-tabs": true,
            "b-tab": true,
            "b-nav": true,
            "b-nav-item": true,
            "b-overlay": true,
            "b-popover": true,
            "b-tooltip": true,
            Portal: true,
            PortalTarget: true,
        },
    };
}

export function suppressDebugConsole() {
    vi.spyOn(console, "debug").mockImplementation(vi.fn());
}

export function suppressBootstrapVueWarnings() {
    const originalWarn = console.warn;
    vi.spyOn(console, "warn").mockImplementation(
        vi.fn((msg) => {
            if (msg.indexOf("BootstrapVue warn") < 0) {
                originalWarn(msg);
            }
        }),
    );
}

export function suppressErrorForCustomIcons() {
    const originalError = console.error;
    vi.spyOn(console, "error").mockImplementation(
        vi.fn((msg) => {
            if (msg.indexOf("Could not find one or more icon(s)") < 0) {
                originalError(msg);
            }
        }),
    );
}

export function suppressLucideVue2Deprecation() {
    const originalWarn = console.warn;
    vi.spyOn(console, "warn").mockImplementation(
        vi.fn((msg) => {
            if (msg.indexOf("[Lucide Vue] This package will be deprecated") < 0) {
                originalWarn(msg);
            }
        }),
    );
}

function isTestLocalized(received) {
    return received && received.indexOf && received.indexOf("test_localized<") == 0;
}

// Custom matchers for localization testing
expect.extend({
    toBeLocalized(received) {
        const pass = isTestLocalized(received);
        if (pass) {
            return {
                message: () => `expected ${received} to be localized`,
                pass: true,
            };
        } else {
            return {
                message: () => `expected ${received} to be localized`,
                pass: false,
            };
        }
    },
    toBeLocalizationOf(received, str) {
        let unlocalized;
        if (received.indexOf("test_localized<") == 0) {
            unlocalized = received.substr("test_localized<".length);
            unlocalized = unlocalized.substr(0, unlocalized.length - 1);
        } else {
            unlocalized = received;
        }
        const pass = testLocalize(str) == received;
        if (pass) {
            return {
                message: () => `expected ${unlocalized} to be localization of ${str}`,
                pass: true,
            };
        } else if (!isTestLocalized(received)) {
            return {
                message: () => `expected ${received} to be localized`,
                pass: false,
            };
        } else {
            return {
                message: () => `expected ${unlocalized} to be localization of ${str}`,
                pass: false,
            };
        }
    },
});

export function dispatchEvent(wrapper, type, props = {}) {
    const event = new Event(type, { bubbles: true });
    Object.assign(event, props);
    wrapper.element.dispatchEvent(event);
}

export function findViaNavigation(wrapper, component) {
    return wrapper.find(component.selector);
}

/**
 * Expect and mock out an API request to /api/configuration. In general, useConfig
 * and using tests/vitest/mockConfig is better since components since be talking to the API
 * directly in this way but some older components are not using the latest composables.
 */
export function expectConfigurationRequest(http, config) {
    return http.get("/api/configuration", ({ response }) => {
        return response(200).json(config);
    });
}

/**
 * Create a test router for Vue 3.
 * For Vue Test Utils v2, pass this to mount options: { global: { plugins: [router] } }
 */
export function createTestRouter(routes = []) {
    // Add a catch-all route to prevent "No match found" warnings
    const defaultRoutes = [{ path: "/:pathMatch(.*)*", name: "not-found", component: { template: "<div></div>" } }];
    return createRouter({
        history: createWebHistory(),
        routes: [...routes, ...defaultRoutes],
    });
}

/**
 * @deprecated Use createTestRouter() instead and pass to global.plugins
 * This function is kept for backward compatibility during migration.
 */
export function injectTestRouter(localVue) {
    // In Vue 3, routers are installed via app.use(), not localVue
    // Return a router that can be passed to mount's global.plugins
    return createTestRouter();
}

/**
 * Waits n milliseconds and then promise resolves
 * Usage: await wait(500);
 */
export const wait = (n) => {
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve();
        }, n);
    });
};

export function mockUnprivilegedToolsRequest(server, http) {
    server.use(
        http.get("/api/unprivileged_tools", ({ response }) => {
            return response(200).json([]);
        }),
    );
}
