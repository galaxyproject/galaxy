import { toValue } from "@vueuse/core";
import { onScopeDispose, ref, watch } from "vue";

export function useFilterObjectArray(array, filter, objectFields, asRegex = false) {
    const worker = new Worker(new URL("./filter.worker.js", import.meta.url));

    const filtered = ref([]);
    filtered.value = toValue(array);

    const post = (message) => {
        worker.postMessage(message);
    };

    watch(
        () => toValue(array),
        (arr) => {
            post({ type: "setArray", array: arr });
        },
        {
            immediate: true,
        }
    );

    watch(
        () => toValue(filter),
        (f) => {
            post({ type: "setFilter", filter: f });
        },
        {
            immediate: true,
        }
    );

    watch(
        () => toValue(objectFields),
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
