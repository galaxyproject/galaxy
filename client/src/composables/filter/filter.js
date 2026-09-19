import { toValue } from "@vueuse/core";
import { onScopeDispose, ref, watch } from "vue";

export function useFilterObjectArray(array, filter, objectFields, asRegex = false) {
    const worker = new Worker(new URL("./filter.worker.js", import.meta.url), { type: "module" });

    const filtered = ref([]);
    filtered.value = toValue(array);

    // Track the latest request so consumers never act on an intermediate result.
    const pending = ref(true);
    let sentSeq = 0;

    const post = (message) => {
        sentSeq += 1;
        pending.value = true;
        worker.postMessage({ ...message, seq: sentSeq });
    };

    watch(
        () => toValue(array),
        (arr) => {
            post({ type: "setArray", array: arr });
        },
        {
            immediate: true,
        },
    );

    watch(
        () => toValue(filter),
        (f) => {
            post({ type: "setFilter", filter: f });
        },
        {
            immediate: true,
        },
    );

    watch(
        () => toValue(objectFields),
        (fields) => {
            post({ type: "setFields", fields });
        },
        {
            immediate: true,
        },
    );

    worker.onmessage = (e) => {
        const message = e.data;

        if (message.type === "result" && message.seq === sentSeq) {
            filtered.value = message.filtered;
            pending.value = false;
        }
    };

    onScopeDispose(() => {
        worker.terminate();
    });

    return { filtered, pending };
}
