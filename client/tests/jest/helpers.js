/**
 * Unit test debugging utilities
 */
import { timer } from "rxjs";
import { take } from "rxjs/operators";
import { shallowMount } from "@vue/test-utils";

export function getNewAttachNode() {
    const attachElement = document.createElement("div");
    if (document.body) {
        document.body.appendChild(attachElement);
    }
    return attachElement;
}

// Creates a watcher on the indicated vm/prop for use in testing
export function watchForChange(vm, propName) {
    const start = new Date();
    return new Promise((resolve) => {
        vm.$watch(propName, function (newVal, oldVal) {
            const stop = new Date();
            resolve({ timeElapsed: stop - start, newVal, oldVal });
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

// Mounts a renderless component with sample content for testing
export async function mountRenderless(component, localVue, propsData) {
    return shallowMount(component, {
        localVue,
        propsData,
        scopedSlots: {
            default: "<div></div>",
        },
    });
}
