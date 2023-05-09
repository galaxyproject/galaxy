import { onScopeDispose, ref, watch } from "vue";
import { resolveUnref } from "@vueuse/core";

/**
 * Reactively filter an array of objects, by comparing `filter` to all `fields`.
 * All parameters can optionally be refs.
 * @param array array of objects to filter
 * @param filter string to filter by
 * @param objectFields string array of fields to filter by on each object
 */
export function useFilterObjectArray(array, filter, objectFields) {
    const worker = new Worker(new URL("./filter.worker.js", import.meta.url));

    const filtered = ref([]);
    filtered.value = resolveUnref(array);

    const post = (message) => {
        worker.postMessage(message);
    };

    watch(
        () => resolveUnref(array),
        (arr) => {
            post({ type: "setArray", array: arr });
        },
        {
            immediate: true,
        }
    );

    watch(
        () => resolveUnref(filter),
        (f) => {
            post({ type: "setFilter", filter: f });
        },
        {
            immediate: true,
        }
    );

    watch(
        () => resolveUnref(objectFields),
        (fields) => {
            post({ type: "setFields", fields });
        },
        {
            immediate: true,
        }
    );

    worker.onmessage = (e) => {
        const message = e.data;

        if (message.type === "result") {
            filtered.value = message.filtered;
        }
    };

    onScopeDispose(() => {
        worker.terminate();
    });

    return filtered;
}
