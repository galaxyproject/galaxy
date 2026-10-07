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
 * Includes Pinia store by default for components that use stores.
 *
 * @returns {import("@vue/test-utils").GlobalMountOptions}
 */
export function getLocalVue(instrumentLocalization = false) {
    const l = instrumentLocalization ? testLocalize : _l;
    const pinia = createPinia();
    setActivePinia(pinia);
    // Vue Router 3 auto-injected a (possibly path-less) $route/$router into every
    // component via a global mixin, so old tests never had to think about it. Vue
    // Router 4 only provides useRoute()/useRouter() when a router is actually
    // installed, so give every test a default one here. Tests that need specific
    // routes still pass their own `router` to mount(); the VTU adapter makes that
    // explicit router take priority over this default.
    const plugins = [[localizationPlugin, l], pinia];
    try {
        plugins.push(createTestRouter());
    } catch {
        // Some tests fully replace the "vue-router" module with vi.mock() using a
        // factory that only defines useRoute/useRouter, without createRouter /
        // createWebHistory. Skip the default router there rather than blowing up
        // every test in the file; those tests already provide their own routing
        // stubs for whatever they need.
    }

    const config = {
        plugins,
        // Render the default slot of stubbed components so tests can still
        // interact with content placed inside the components they stub.
        renderStubDefaultSlot: true,
        directives: {
            "b-tooltip": mockedDirective,
            "b-popover": mockedDirective,
        },
        stubs: {
            // bootstrap-vue components render for real (through the compat shim in
            // patches/bootstrap-vue), so tests assert on the markup users get.
            // Stubbing them hid real bugs, like pagination links with no click
            // listener.
            Portal: true,
            PortalTarget: true,
        },
    };

    return config;
}

export function suppressDebugConsole() {
    vi.spyOn(console, "debug").mockImplementation(() => {});
}

export function suppressBootstrapVueWarnings() {
    const originalWarn = console.warn;
    vi.spyOn(console, "warn").mockImplementation((msg) => {
        if (!String(msg).includes("BootstrapVue warn")) {
            originalWarn(msg);
        }
    });
}

export function suppressErrorForCustomIcons() {
    const originalError = console.error;
    vi.spyOn(console, "error").mockImplementation((msg) => {
        if (!String(msg).includes("Could not find one or more icon(s)")) {
            originalError(msg);
        }
    });
}

export function suppressLucideVue2Deprecation() {
    const originalWarn = console.warn;
    vi.spyOn(console, "warn").mockImplementation((msg) => {
        if (String(msg).includes("[Lucide Vue] This package will be deprecated")) {
            return;
        }
        if (String(msg).includes("[Vue warn]")) {
            return;
        }
        originalWarn(msg);
    });
}

export function suppressExpectedErrorMessages(expectedMessages = []) {
    const originalError = console.error;
    vi.spyOn(console, "error").mockImplementation((msg) => {
        if (!expectedMessages.some((expected) => String(msg).includes(expected))) {
            originalError(msg);
        }
    });
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

/**
 * The item at `index`, failing with a clear message when it's missing. Use it
 * for `findAll()` results and `emitted()` lists instead of a bare `[i]`/`.at(i)`,
 * which is typed as possibly undefined and fails later with a vaguer error.
 * @template T
 * @param {ArrayLike<T> | undefined} items
 * @param {number} index
 * @returns {T}
 */
export function nth(items, index) {
    const item = items?.[index < 0 ? items.length + index : index];
    if (item === undefined) {
        throw new Error(`Expected an item at index ${index}, but there are ${items?.length ?? 0}.`);
    }
    return item;
}

/**
 * The first argument of the `index`-th emission of `event` (negative counts
 * from the end), failing with a clear message when it wasn't emitted that often.
 * @param {{ emitted: (event: string) => unknown[][] | undefined }} wrapper
 * @param {string} event
 * @param {number} [index]
 * @returns {unknown}
 */
export function emittedArg(wrapper, event, index = 0) {
    const emissions = wrapper.emitted(event) ?? [];
    const args = emissions[index < 0 ? emissions.length + index : index];
    if (args === undefined) {
        throw new Error(`Expected "${event}" emission ${index}, but it was emitted ${emissions.length} times.`);
    }
    return args[0];
}

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
 * getLocalVue()'s global mount options with `plugins` added, where a test's own
 * pinia or router replaces the default of the same kind. Use it as
 * `mount(Component, { global: withPlugins(localVue, pinia) })`.
 * @template {{ plugins?: any[] }} G
 * @param {G} localVue
 * @param {...any} plugins
 * @returns {G}
 */
export function withPlugins(localVue, ...plugins) {
    const isPinia = (plugin) => plugin && typeof plugin === "object" && "_s" in plugin && "_e" in plugin;
    const isRouter = (plugin) => plugin && typeof plugin === "object" && "currentRoute" in plugin && "push" in plugin;
    const replaced = (plugin) =>
        plugins.some((own) => (isPinia(plugin) && isPinia(own)) || (isRouter(plugin) && isRouter(own)));
    return { ...localVue, plugins: [...(localVue.plugins ?? []).filter((plugin) => !replaced(plugin)), ...plugins] };
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
