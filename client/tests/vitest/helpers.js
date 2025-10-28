// Vitest-compatible test helpers for Vue 3
// Based on tests/jest/helpers.js but adapted for Vitest
import { shallowMount } from "@vue/test-utils";
import BootstrapVue from "bootstrap-vue";
import { iconPlugin } from "@/components/plugins/icons";
import { localizationPlugin } from "@/components/plugins/localization";
import { vueRxShortcutPlugin } from "@/components/plugins/vueRxShortcuts";
import { createPinia } from "pinia";
import _l from "@/utils/localization";
import { createRouter, createMemoryHistory } from "vue-router";
import { vi, expect } from "vitest";

// Test localization function
function testLocalize(text) {
    if (text) {
        return `test_localized<${text}>`;
    } else {
        return text;
    }
}

function isTestLocalized(text) {
    return text && text.indexOf("test_localized<") == 0;
}

// Custom vitest matchers for localization
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
    toContainLocalizationOf(received, str) {
        const pass = received.indexOf(testLocalize(str)) >= 0;
        if (pass) {
            return {
                message: () => `expected ${received} to contain localization of ${str}`,
                pass: true,
            };
        } else {
            return {
                message: () => `expected ${received} to contain localization of ${str}`,
                pass: false,
            };
        }
    },
});

// Gets Vue Test Utils global configuration for Vue 3
export function getLocalVue(options = {}) {
    // options can be a boolean for backward compatibility with old instrumentLocalization flag
    if (typeof options === "boolean") {
        options = { instrumentLocalization: options };
    }
    const { instrumentLocalization = false, withPinia = true } = options;

    const mockedDirective = {
        beforeMount(el, binding) {
            el.setAttribute("data-mock-directive", binding.value || el.title);
        },
    };

    const l = instrumentLocalization ? testLocalize : _l;

    // Create a basic router for tests - use MemoryHistory for tests
    const router = createRouter({
        history: createMemoryHistory(),
        routes: [],
    });

    const plugins = [router, BootstrapVue, [localizationPlugin, l], vueRxShortcutPlugin, iconPlugin];
    if (withPinia) {
        plugins.unshift(createPinia());
    }

    // Return global config object for Vue Test Utils v2
    return {
        global: {
            plugins: plugins,
            directives: {
                "b-tooltip": mockedDirective,
                "b-popover": mockedDirective,
            },
            stubs: {},
        },
    };
}

// Mounts a renderless component with sample content for testing
export function mountRenderless(component, mountConfig = {}) {
    const globalConfig = getLocalVue();
    return shallowMount(component, {
        ...globalConfig,
        ...mountConfig,
        slots: {
            default: "<div></div>",
        },
    });
}

// Return a new mocked out router for Vue 3
export function injectTestRouter() {
    const router = createRouter({
        history: createMemoryHistory(),
        routes: [],
    });
    return router;
}

// Get local Vue config with router included
export function getLocalVueWithRouter(instrumentLocalization = false) {
    const config = getLocalVue(instrumentLocalization);
    const router = injectTestRouter();
    return {
        global: {
            ...config.global,
            plugins: [...config.global.plugins, router],
        },
    };
}
