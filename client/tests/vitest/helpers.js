/**
 * Unit test debugging utilities for Vitest
 */
import { createLocalVue } from "@vue/test-utils";
import BootstrapVue from "bootstrap-vue";
import { localizationPlugin } from "@/components/plugins/localization";
import { vueRxShortcutPlugin } from "@/components/plugins/vueRxShortcuts";
import { PiniaVuePlugin } from "pinia";
import _l from "@/utils/localization";
import { vi } from "vitest";

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
