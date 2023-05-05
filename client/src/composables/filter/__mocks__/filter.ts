import { resolveUnref, type MaybeComputedRef } from "@vueuse/core";
import { computed } from "vue";
import { runFilter } from "../filterFunction";

/*
    Annoyingly, jest does not support web workers,
    which is why we require this mock.
    It uses the same function as the worker,
    but directly

    The filter module needs to be mocked in the
    test, for this mock to be used.
*/

export function useFilterObjectArray<O extends object, K extends keyof O>(
    array: MaybeComputedRef<Array<O>>,
    filter: MaybeComputedRef<string>,
    objectFields: MaybeComputedRef<Array<K>>
) {
    const filtered = computed(() => {
        const arr = resolveUnref(array);
        const f = resolveUnref(filter);
        const fields = resolveUnref(objectFields);

        return runFilter(f, arr, fields);
    });

    return filtered;
}
