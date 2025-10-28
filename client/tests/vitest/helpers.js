// Vitest-compatible test helpers
// This is a port of Jest helpers to work with Vitest
import { createLocalVue, mount, Wrapper } from "@vue/test-utils";
import BootstrapVue from "bootstrap-vue";
import { createPinia } from "pinia";
import Vue from "vue";
import VueRouter from "vue-router";
import { vi } from "vitest";
import { expect } from "vitest";

// Mock localize function
const mockLocalize = (text) => text;

// Import composables and utils
import { useConfig } from "@/composables/config";

// Setup Bootstrap Vue components we use in tests
const bComponents = {
    BAlert: BootstrapVue.BAlert,
    BButton: BootstrapVue.BButton,
    BButtonGroup: BootstrapVue.BButtonGroup,
    BCard: BootstrapVue.BCard,
    BCardBody: BootstrapVue.BCardBody,
    BCardFooter: BootstrapVue.BCardFooter,
    BCardHeader: BootstrapVue.BCardHeader,
    BCardText: BootstrapVue.BCardText,
    BCol: BootstrapVue.BCol,
    BCollapse: BootstrapVue.BCollapse,
    BContainer: BootstrapVue.BContainer,
    BDropdown: BootstrapVue.BDropdown,
    BDropdownDivider: BootstrapVue.BDropdownDivider,
    BDropdownItem: BootstrapVue.BDropdownItem,
    BDropdownText: BootstrapVue.BDropdownText,
    BFormCheckbox: BootstrapVue.BFormCheckbox,
    BFormCheckboxGroup: BootstrapVue.BFormCheckboxGroup,
    BFormGroup: BootstrapVue.BFormGroup,
    BFormInput: BootstrapVue.BFormInput,
    BFormRadio: BootstrapVue.BFormRadio,
    BFormRadioGroup: BootstrapVue.BFormRadioGroup,
    BFormSelect: BootstrapVue.BFormSelect,
    BFormSelectOption: BootstrapVue.BFormSelectOption,
    BFormTextarea: BootstrapVue.BFormTextarea,
    BInputGroup: BootstrapVue.BInputGroup,
    BInputGroupAppend: BootstrapVue.BInputGroupAppend,
    BInputGroupPrepend: BootstrapVue.BInputGroupPrepend,
    BLink: BootstrapVue.BLink,
    BListGroup: BootstrapVue.BListGroup,
    BListGroupItem: BootstrapVue.BListGroupItem,
    BModal: BootstrapVue.BModal,
    BNav: BootstrapVue.BNav,
    BNavItem: BootstrapVue.BNavItem,
    BNavbar: BootstrapVue.BNavbar,
    BPagination: BootstrapVue.BPagination,
    BPopover: BootstrapVue.BPopover,
    BRow: BootstrapVue.BRow,
    BSpinner: BootstrapVue.BSpinner,
    BTab: BootstrapVue.BTab,
    BTable: BootstrapVue.BTable,
    BTabs: BootstrapVue.BTabs,
    BTooltip: BootstrapVue.BTooltip,
};

const bDirectives = {
    VBModal: BootstrapVue.VBModal,
    VBPopover: BootstrapVue.VBPopover,
    VBTooltip: BootstrapVue.VBTooltip,
};

/**
 * Gets a new test localVue instance with common plugins
 * @param {boolean} withRouter - whether to include router
 * @returns {VueConstructor} localVue instance
 */
export function getLocalVue(withRouter = false) {
    const localVue = createLocalVue();
    
    // Add Bootstrap Vue components
    Object.entries(bComponents).forEach(([name, component]) => {
        localVue.component(name, component);
    });
    
    // Add Bootstrap Vue directives
    Object.entries(bDirectives).forEach(([name, directive]) => {
        localVue.directive(name, directive);
    });
    
    // Add Pinia
    localVue.use(createPinia());
    
    // Add localization
    localVue.directive("localize", {
        bind(el, binding) {
            el.textContent = mockLocalize(binding.value);
        },
        update(el, binding) {
            el.textContent = mockLocalize(binding.value);
        },
    });
    
    localVue.filter("localize", mockLocalize);
    localVue.prototype.l = mockLocalize;
    localVue.prototype.localize = mockLocalize;
    
    // Add router if requested
    if (withRouter) {
        localVue.use(VueRouter);
    }
    
    return localVue;
}

/**
 * Custom matchers for localization
 */
expect.extend({
    toBeLocalized(received) {
        const pass = typeof received === "string" && received.length > 0;
        return {
            pass,
            message: () => pass 
                ? `expected ${received} not to be localized`
                : `expected ${received} to be localized`,
        };
    },
    
    toBeLocalizationOf(received, expected) {
        const pass = received === expected; // Since we mock localize to return input
        return {
            pass,
            message: () => pass
                ? `expected ${received} not to be localization of ${expected}`
                : `expected ${received} to be localization of ${expected}`,
        };
    },
    
    toContainLocalizationOf(received, expected) {
        const pass = received.includes(expected);
        return {
            pass,
            message: () => pass
                ? `expected ${received} not to contain localization of ${expected}`
                : `expected ${received} to contain localization of ${expected}`,
        };
    },
});

/**
 * Mount a renderless component (no template)
 */
export async function mountRenderless(component, options = {}) {
    const { localVue = getLocalVue(), ...rest } = options;
    const wrapper = mount(component, {
        localVue,
        ...rest,
    });
    await wrapper.vm.$nextTick();
    return wrapper;
}

/**
 * Utility to wait for a specific time
 */
export function wait(ms = 0) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Wait for a lifecycle event on a component
 */
export async function waitForLifecyleEvent(wrapper, lifecycleHook) {
    return new Promise((resolve) => {
        const vm = wrapper.vm;
        vm.$options[lifecycleHook] = vm.$options[lifecycleHook] || [];
        vm.$options[lifecycleHook].push(resolve);
    });
}

/**
 * Watch for a specific change in component
 */
export async function watchForChange(wrapper, watchSpec) {
    const vm = wrapper.vm;
    return new Promise((resolve) => {
        vm.$watch(watchSpec, (newVal) => {
            resolve(newVal);
        });
    });
}

/**
 * Watch until a condition is met
 */
export async function watchUntil(wrapper, watchSpec, condition) {
    const vm = wrapper.vm;
    return new Promise((resolve) => {
        const unwatch = vm.$watch(watchSpec, (newVal) => {
            if (condition(newVal)) {
                unwatch();
                resolve(newVal);
            }
        });
    });
}

/**
 * Mock Vuex module
 */
export function mockModule(moduleId, mockImplementation) {
    vi.doMock(`@/store/modules/${moduleId}`, () => ({
        default: mockImplementation,
    }));
}

/**
 * Dispatch browser event
 */
export function dispatchEvent(wrapper, type, options = {}) {
    const event = new Event(type, { bubbles: true, cancelable: true, ...options });
    wrapper.element.dispatchEvent(event);
}

/**
 * Get element by selector
 */
export function getElement(wrapper, selector) {
    return wrapper.find(selector).element;
}

/**
 * Debug helpers
 */
export function show(wrapper, selector) {
    if (selector) {
        console.log(wrapper.find(selector).html());
    } else {
        console.log(wrapper.html());
    }
}

export function showComputed(wrapper, computedName) {
    console.log(wrapper.vm[computedName]);
}

export function showData(wrapper, dataName) {
    console.log(wrapper.vm[dataName]);
}

export function showAll(wrapper) {
    console.log("HTML:", wrapper.html());
    console.log("Props:", wrapper.props());
    console.log("Data:", wrapper.vm.$data);
    console.log("Computed:", Object.keys(wrapper.vm.$options.computed || {}));
}

/**
 * Suppress console methods
 */
export function suppressConsoleLogs() {
    const originalLog = console.log;
    beforeAll(() => {
        console.log = vi.fn();
    });
    afterAll(() => {
        console.log = originalLog;
    });
}

export function suppressConsoleWarns() {
    const originalWarn = console.warn;
    beforeAll(() => {
        console.warn = vi.fn();
    });
    afterAll(() => {
        console.warn = originalWarn;
    });
}

export function suppressConsoleErrors() {
    const originalError = console.error;
    beforeAll(() => {
        console.error = vi.fn();
    });
    afterAll(() => {
        console.error = originalError;
    });
}

/**
 * Mock configuration request
 */
export function expectConfigurationRequest(config = {}) {
    vi.mocked(useConfig).mockReturnValue({
        config: { ...config },
        isConfigLoaded: true,
    });
}

/**
 * Inject test router
 */
export function injectTestRouter(localVue, routes = []) {
    const router = new VueRouter({ routes, mode: "abstract" });
    return { localVue, router };
}

/**
 * Wait for N emissions of an event
 */
export async function untilNthEmission(wrapper, eventName, n = 1) {
    const emissions = [];
    return new Promise((resolve) => {
        let count = 0;
        wrapper.vm.$on(eventName, (payload) => {
            count++;
            emissions.push(payload);
            if (count === n) {
                resolve(emissions);
            }
        });
    });
}

// Re-export some common utilities
export { mount, shallowMount, createLocalVue } from "@vue/test-utils";
export { flushPromises } from "flush-promises";
export { vi } from "vitest";