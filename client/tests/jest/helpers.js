/**
 * Unit test debugging utilities
 */
import { timer, fromEventPattern } from "rxjs";
import { take, debounceTime, takeUntil } from "rxjs/operators";
import { createLocalVue, shallowMount } from "@vue/test-utils";
import { localizationPlugin } from "components/plugins/localization";
import { vueRxShortcutPlugin } from "components/plugins/vueRxShortcuts";
import { eventHubPlugin } from "components/plugins/eventHub";
import { iconPlugin } from "components/plugins/icons";
import BootstrapVue from "bootstrap-vue";
import Vuex from "vuex";
import _l from "utils/localization";
import { PiniaVuePlugin } from "pinia";

const defaultComparator = (a, b) => a == b;

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
            opts
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

// Gets a localVue with custom directives
export function getLocalVue(instrumentLocalization = false) {
    const localVue = createLocalVue();
    const mockedDirective = {
        bind() {},
    };
    localVue.use(PiniaVuePlugin);
    localVue.use(Vuex);
    localVue.use(BootstrapVue);
    const l = instrumentLocalization ? testLocalize : _l;
    localVue.use(localizationPlugin, l);
    localVue.use(vueRxShortcutPlugin);
    localVue.use(eventHubPlugin);
    localVue.use(iconPlugin);
    localVue.directive("b-tooltip", mockedDirective);
    localVue.directive("b-popover", mockedDirective);
    return localVue;
}

// Mounts a renderless component with sample content for testing
export function mountRenderless(component, mountConfig = {}) {
    const { localVue = getLocalVue(), ...otherConfig } = mountConfig;
    return shallowMount(component, {
        localVue,
        ...otherConfig,
        scopedSlots: {
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
