import { computed } from "vue";
import type { MaybeComputedRef } from "@vueuse/core";
import { resolveUnref } from "@vueuse/core";

/**
 * Reactively filter an array of objects, by comparing `filter` to all `fields`.
 * All parameters can optionally be refs.
 * @param array array of objects to filter
 * @param filter string to filter by
 * @param objectFields string array of fields to filter by on each object
 */
export function useFilterObjectArray<O extends object, K extends keyof O>(
    array: MaybeComputedRef<Array<O>>,
    filter: MaybeComputedRef<string>,
    objectFields: MaybeComputedRef<Array<K>>
) {
    const filtered = computed(() => {
        const f = resolveUnref(filter).toLowerCase();
        const arr = resolveUnref(array);
        const fields = resolveUnref(objectFields);

        if (f === "") {
            return arr;
        } else {
            return arr.filter((obj) => {
                for (const field of fields) {
                    const val = obj[field];

                    if (typeof val === "string" && val.toLowerCase().includes(f)) {
                        return true;
                    }
                }

                return false;
            });
        }
    });

    return filtered;
}
