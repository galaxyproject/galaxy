/**
 * Unit test debugging utilities
 */
import { timer, fromEventPattern } from "rxjs";
import { take, debounceTime, takeUntil } from "rxjs/operators";
import { createLocalVue, shallowMount } from "@vue/test-utils";
import { localizationPlugin } from "components/plugins/localization";

// Creates a watcher on the indicated vm/prop for use in testing
export function watchForChange({ vm, opts, propName, timeout = 1000, label = "" }) {
    const start = new Date();
    return new Promise((resolve, reject) => {
        const timeoutID = setTimeout(() => {
            reject(`${propName} never changed ${label}`);
        }, timeout);
        vm.$watch(
            propName,
            function (newVal, oldVal) {
                if (newVal !== oldVal) {
                    clearTimeout(timeoutID);
                    const stop = new Date();
                    resolve({ start, stop, propName, elapsed: stop - start, newVal, oldVal });
                }
            },
            opts
        );
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
    localVue.directive("b-tooltip", mockedDirective);
    localVue.directive("b-popover", mockedDirective);
    localVue.use(localizationPlugin);
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
