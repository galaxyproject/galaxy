/**
 * Unit test debugging utilities for Vitest
 */
import { createLocalVue } from "@vue/test-utils";
import BootstrapVue from "bootstrap-vue";
import { PiniaVuePlugin } from "pinia";
import { vi } from "vitest";
import VueRouter from "vue-router";

import { localizationPlugin } from "@/components/plugins/localization";
import _short from "@/components/plugins/short";
import { vueRxShortcutPlugin } from "@/components/plugins/vueRxShortcuts";
import _l from "@/utils/localization";

function testLocalize(text) {
    if (text) {
        return `test_localized<${text}>`;
    } else {
        return text;
    }
}

// Gets a localVue with custom directives
export function getLocalVue(instrumentLocalization = false) {
    const localVue = createLocalVue();
    const mockedDirective = {
        bind(el, binding) {
            el.setAttribute("data-mock-directive", binding.value || el.title);
        },
    };
    localVue.use(PiniaVuePlugin);
    localVue.use(BootstrapVue);
    const l = instrumentLocalization ? testLocalize : _l;
    localVue.use(localizationPlugin, l);
    localVue.use(vueRxShortcutPlugin);
    localVue.directive("b-tooltip", mockedDirective);
    localVue.directive("b-popover", mockedDirective);
    return localVue;
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

/**
 * Return a new mocked out router attached to the specified localVue instance.
 */
export function injectTestRouter(localVue) {
    localVue.use(VueRouter);
    const router = new VueRouter();
    return router;
}
