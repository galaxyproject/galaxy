import { computed, unref } from "vue";

/**
 * Reactively filter an array of objects, by comparing `filter` to all `fields`.
 * All parameters can optionally be refs.
 * @param array array of objects to filter
 * @param filter string to filter by
 * @param objectFields string array of fields to filter by on each object
 */
export function useFilterObjectArray(array, filter, objectFields) {
    const filtered = computed(() => {
        const f = unref(filter).toLowerCase();
        const arr = unref(array);
        const fields = unref(objectFields);

        if (f === "") {
            return arr;
        } else {
            return arr.filter((obj) => {
                for (const field of fields) {
                    if (obj[field].toLowerCase().includes(f)) {
                        return true;
                    }
                }

                return false;
            });
        }
    });

    return filtered;
}
