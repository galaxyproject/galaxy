/**
 * Unit test debugging utilities
 */
import { shallowMount } from "@vue/test-utils";
import BootstrapVue from "bootstrap-vue";
import { iconPlugin } from "components/plugins/icons";
import { localizationPlugin } from "components/plugins/localization";
import { vueRxShortcutPlugin } from "components/plugins/vueRxShortcuts";
import { createPinia } from "pinia";
import { fromEventPattern, timer } from "rxjs";
import { debounceTime, take, takeUntil } from "rxjs/operators";
import _l from "utils/localization";
import { createRouter, createWebHistory } from "vue-router";

import _short from "@/components/plugins/short";

const defaultComparator = (a, b) => a == b;

export function dispatchEvent(wrapper, type, props = {}) {
    const event = new Event(type, { bubbles: true });
    Object.assign(event, props);
    wrapper.element.dispatchEvent(event);
}

export function findViaNavigation(wrapper, component) {
    return wrapper.find(component.selector);
}

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

// Creates a watcher on the indicated vm/prop for use in testing
export function watchForChange(cfg = {}) {
    const { vm, opts, propName, comparator = defaultComparator, timeout = 1000 } = cfg;

    const start = new Date();
    return new Promise((resolve, reject) => {
        const timeoutID = setTimeout(() => {
            reject(`${propName} never changed`);
        }, timeout);

        vm.$watch(
            propName,
            function (newVal, oldVal) {
                if (!comparator(newVal, oldVal)) {
                    clearTimeout(timeoutID);
                    const stop = new Date();
                    resolve({ start, stop, propName, elapsed: stop - start, newVal, oldVal });
                }
            },
            opts,
        );
    });
}

export function watchUntil(vm, isComplete, timeout = 1000) {
    const start = new Date();

    return new Promise((resolve, reject) => {
        const timeoutID = setTimeout(() => {
            if (unwatch) {
                unwatch();
            }
            reject("watch timed out");
        }, timeout);

        const unwatch = vm.$watch(isComplete, (isDone) => {
            if (!isDone) {
                return;
            }
            clearTimeout(timeoutID);
            const stop = new Date();
            if (unwatch) {
                unwatch();
            }
            resolve({ start, stop, elapsed: stop - start });
        });
    });
}

// formats a console.log to more easily read the passed object
export const show = (obj) => console.log(JSON.stringify(obj, null, 4));

// gets comuted props from a Vue component
export const getComputed = (vm) => {
    return Object.keys(vm.$options.computed || {}).reduce((acc, key) => {
        return { ...acc, [key]: vm[key] };
    }, {});
};

// show all computed vals for passed vm
export const showComputed = (vm) => show(getComputed(vm));

// Shows vue data props
export const showData = (vm) => show(vm._data || {});

// Shows all reactive props in a vue instance
export const showAll = (vm) => {
    show({
        props: vm._props,
        computed: getComputed(vm),
        data: vm._data,
    });
};

// waits n milliseconds and then promise resolves
// usage: await wait(500);
export const wait = (n) => {
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve();
        }, n);
    });
};

// Gets Vue Test Utils global configuration for Vue 3
export function getLocalVue(instrumentLocalization = false) {
    const mockedDirective = {
        beforeMount(el, binding) {
            el.setAttribute("data-mock-directive", binding.value || el.title);
        },
    };

    const l = instrumentLocalization ? testLocalize : _l;

    // Return global config object for Vue Test Utils v2
    return {
        global: {
            plugins: [createPinia(), BootstrapVue, [localizationPlugin, l], vueRxShortcutPlugin, iconPlugin],
            directives: {
                "b-tooltip": mockedDirective,
                "b-popover": mockedDirective,
            },
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

// waits for indicated event to stop firing
export function waitForLifecyleEvent(vm, lifecycleHookName, cfg = {}) {
    const { debouncePeriod = 50, timeoutPeriod = 1000 } = cfg;

    const evtName = `hook:${lifecycleHookName}`;
    const addHandler = (fn) => vm.$on(evtName, fn);
    const removeHandler = (fn) => vm.$off(evtName, fn);
    const hook$ = fromEventPattern(addHandler, removeHandler);

    // prettier-ignore
    return hook$.pipe(
        debounceTime(debouncePeriod),
        take(1),
        takeUntil(timer(timeoutPeriod))
    )
    .toPromise();
}

// Waits for an observable to emit N times then resolves a promise
// returns a promise because it's easier to test that way in async jest tests
export const untilNthEmission = (src$, n = 1, safetyTimeout = 2000) => {
    return new Promise((resolve, reject) => {
        let result;
        // prettier-ignore
        src$.pipe(
            take(n),
            takeUntil(timer(safetyTimeout))
        ).subscribe({
            next: (val) => (result = val),
            complete: () => resolve(result),
            error: reject,
        });
    });
};

/**
 * Build a namespaced store module with mock actions.
 * Optionally takes a default state.
 */
export function mockModule(storeModule, state = {}) {
    const actions = {};

    for (const key in storeModule.actions) {
        if (Object.hasOwnProperty.call(storeModule.actions, key)) {
            actions[key] = jest.fn();
        }
    }

    return {
        state,
        getters: storeModule.getters,
        mutations: storeModule.mutations,
        actions,
        namespaced: true,
    };
}

/**
 * Expect and mock out an API request to /api/configuration. In general, useConfig
 * and using tests/jest/mockConfig is better since components since be talking to the API
 * directly in this way but some older components are not using the latest composables.
 */
export function expectConfigurationRequest(http, config) {
    return http.get("/api/configuration", ({ response }) => {
        return response(200).json(config);
    });
}

export function mockUnprivilegedToolsRequest(server, http) {
    server.use(
        http.get("/api/unprivileged_tools", ({ response }) => {
            return response(200).json([]);
        }),
    );
}

/**
 * Mock the current user API request with a test user
 * @param {Object} server - MSW server instance
 * @param {Object} http - MSW http instance
 * @param {Object} userOverrides - Optional overrides for the user object
 */
export function mockCurrentUserRequest(server, http, userOverrides = {}) {
    const defaultUser = {
        id: "test-user-id",
        email: "test@example.com",
        username: "testuser",
        is_admin: false,
        preferences: {
            favorites: JSON.stringify({ tools: [] }),
        },
        ...userOverrides,
    };

    server.use(
        http.get("/api/users/:userId", ({ response }) => {
            return response(200).json(defaultUser);
        }),
    );
}

/**
 * Return a new mocked out router for Vue 3.
 */
export function injectTestRouter() {
    const router = createRouter({
        history: createWebHistory(),
        routes: [],
    });
    return router;
}

export function suppressDebugConsole() {
    jest.spyOn(console, "debug").mockImplementation(jest.fn());
}

export function suppressBootstrapVueWarnings() {
    // Simply mock console.warn to do nothing to avoid circular call issues
    jest.spyOn(console, "warn").mockImplementation(() => {});
}

export function suppressErrorForCustomIcons() {
    // Restore console.error first if it's already mocked
    if (console.error.mockRestore) {
        console.error.mockRestore();
    }
    const originalError = console.error;
    jest.spyOn(console, "error").mockImplementation((msg) => {
        if (msg && typeof msg === "string" && msg.indexOf("Could not find one or more icon(s)") < 0) {
            originalError(msg);
        }
    });
}

export function suppressLucideVue2Deprecation() {
    const originalWarn = console.warn;
    jest.spyOn(console, "warn").mockImplementation(
        jest.fn((msg) => {
            if (msg.indexOf("[Lucide Vue] This package will be deprecated") < 0) {
                originalWarn(msg);
            }
        }),
    );
}
