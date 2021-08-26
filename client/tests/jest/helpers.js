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

const defaultComparator = (a, b) => a == b;

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
            if (unwatch) unwatch();
            reject("watch timed out");
        }, timeout);

        const unwatch = vm.$watch(isComplete, (isDone) => {
            if (!isDone) return;
            clearTimeout(timeoutID);
            const stop = new Date();
            if (unwatch) unwatch();
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
export const wait = (n) => timer(n).pipe(take(1)).toPromise();

// Gets a localVue with custom directives
export function getLocalVue() {
    const localVue = createLocalVue();
    const mockedDirective = {
        bind() {},
    };
    localVue.use(Vuex);
    localVue.use(BootstrapVue);
    localVue.use(localizationPlugin);
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
