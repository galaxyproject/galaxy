import { computed, unref } from "vue";

/**
 * Filter array of objects, by comparing `filter` to all `fields`
 */
export function useFilterObjectArray(array, filter, objectFields) {
    const filtered = computed(() => {
        const f = unref(filter);
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
