/**
 * Unit test debugging utilities for Vitest
 *
 * Note: For Vue 3 / Vue Test Utils v2, we no longer use createLocalVue.
 * Instead, plugins are passed via the `global` mount option.
 *
 * Usage: mount(Component, { global: getLocalVue() })
 */
import { createPinia, setActivePinia } from "pinia";
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
 *
 * Includes Pinia store by default for components that use stores.
 *
 * For backward compatibility with Vue 2 patterns, the returned object
 * has a .use() method that adds plugins (no-op in most cases since
 * plugins should be passed via the adapter).
 */
export function getLocalVue(instrumentLocalization = false) {
    const l = instrumentLocalization ? testLocalize : _l;
    const pinia = createPinia();
    setActivePinia(pinia);

    const config = {
        plugins: [[localizationPlugin, l], pinia],
        directives: {
            "b-tooltip": mockedDirective,
            "b-popover": mockedDirective,
        },
        stubs: {
            // Stub common bootstrap-vue components (both kebab-case and PascalCase)
            "b-button": true,
            BButton: true,
            "b-form-input": true,
            BFormInput: true,
            "b-form-checkbox": true,
            BFormCheckbox: true,
            "b-modal": true,
            BModal: true,
            "b-card": true,
            BCard: true,
            "b-dropdown": true,
            BDropdown: true,
            "b-dropdown-item": true,
            BDropdownItem: true,
            "b-alert": true,
            BAlert: true,
            "b-badge": true,
            BBadge: true,
            "b-spinner": true,
            BSpinner: true,
            "b-link": true,
            BLink: true,
            "b-collapse": true,
            BCollapse: true,
            "b-form-group": true,
            BFormGroup: true,
            "b-form-select": true,
            BFormSelect: true,
            "b-form-textarea": true,
            BFormTextarea: true,
            "b-table": true,
            BTable: true,
            "b-pagination": true,
            BPagination: true,
            "b-tabs": true,
            BTabs: true,
            "b-tab": true,
            BTab: true,
            "b-nav": true,
            BNav: true,
            "b-nav-item": true,
            BNavItem: true,
            "b-overlay": true,
            BOverlay: true,
            "b-popover": true,
            BPopover: true,
            "b-tooltip": true,
            BTooltip: true,
            "b-form-row": true,
            BFormRow: true,
            Portal: true,
            PortalTarget: true,
        },
        // Vue 2 compatibility: .use() method for localVue.use(Plugin)
        // This is a no-op since the VTU adapter handles plugin registration
        use(plugin) {
            // For VueRouter, the adapter handles it via the router mount option
            // For other plugins, they should be passed via mount options
            // This method exists only to prevent "localVue.use is not a function" errors
            return config;
        },
    };

    return config;
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
            // Filter out Lucide deprecation warnings
            if (msg && msg.indexOf && msg.indexOf("[Lucide Vue] This package will be deprecated") >= 0) {
                return;
            }
            // Filter out Vue compat warnings (they shouldn't fail tests during migration)
            if (msg && msg.indexOf && msg.indexOf("[Vue warn]") >= 0) {
                return;
            }
            originalWarn(msg);
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
